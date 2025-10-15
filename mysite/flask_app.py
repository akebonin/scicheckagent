# flask_app (1).py
from flask import Flask, request, render_template, send_file, Response, session, jsonify, redirect, url_for
from dotenv import load_dotenv
import os
import requests
import io
import json
from urllib.parse import quote_plus
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.units import inch
from reportlab.lib import colors
import logging
import re
import uuid
import time
from bs4 import BeautifulSoup
import sqlite3

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
# Ensure this path is correct for your PythonAnywhere setup
load_dotenv(dotenv_path="/home/scicheckagent/mysite/.env")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24))
DATABASE_NAME = 'scicheck_cache.db'

# ---- Database Helper Functions ----
def get_db_connection():
    """Establishes a connection to the SQLite database."""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logging.error(f"Database connection error: {e}")
        return None

# ---- API Configuration and Prompts ----
OR_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# REFACTORED: Consolidate common instructions
BASE_EXTRACTION_RULES = '''
**Strict rules:**
- ONLY include claims that appear EXPLICITLY in the text.
- Each claim must be explicitly stated.
- If no explicit, complete, testable claims exist, output exactly: "No explicit claims found."
- Absolutely DO NOT infer, paraphrase, generalize, or introduce external knowledge.
- NEVER include incomplete sentences, headings, summaries, conclusions, speculations, questions, or introductory remarks.
- Output ONLY the claims formatted as a numbered list, or "No explicit claims found."
'''

extraction_templates = {
    "General Analysis of Testable Claims": f"You will be given a text. Extract a **numbered list** of explicit, scientifically testable claims.\n{BASE_EXTRACTION_RULES}\nTEXT:\n{{text}}\nOUTPUT:",
    "Specific Focus on Scientific Claims": f"You will be given a text. Extract a **numbered list** of explicit, scientifically testable claims related to science.\n{BASE_EXTRACTION_RULES}\nTEXT:\n{{text}}\nOUTPUT:",
    "Technology-Focused Extraction": f"You will be given a text. Extract a **numbered list** of explicit, testable claims related to technology.\n{BASE_EXTRACTION_RULES}\nTEXT:\n{{text}}\nOUTPUT:"
}

BASE_VERIFICATION_JSON_INSTRUCTIONS = '''
Your response MUST be a single, valid JSON object with NO additional text or explanations before or after it.
The JSON object must contain the following keys:
- "verdict": A string containing ONLY ONE of the allowed verdict options.
- "justification": A concise justification (max 1000 characters). Embed full source URLs directly in the justification text if you cite them.
- "sources": A list of 1-2 directly relevant and clickable source URLs. If none, provide an empty list [].
- "keywords": A list of 3-5 highly relevant scientific keywords or short phrases for external search.
'''

# --- CORRECTED CODE ---
# The `.format()` call is removed from the dictionary definition.
# The templates now correctly contain the {claim} and {json_instructions} placeholders.
verification_prompts = {
    "General Analysis of Testable Claims": '''
Assess the scientific accuracy of the claim.
Allowed verdicts: "VERIFIED", "PARTIALLY SUPPORTED", "INCONCLUSIVE", "CONTRADICTED".
{json_instructions}
Claim: "{claim}"
''',
    "Specific Focus on Scientific Claims": '''
Assess if the scientific claim is supported by current evidence.
Allowed verdicts: "SUPPORTED", "INCONCLUSIVE", "NOT SUPPORTED".
{json_instructions}
Claim: "{claim}"
''',
    "Technology-Focused Extraction": '''
Evaluate the plausibility of this technology-related claim.
Allowed verdicts: "FEASIBLE", "POSSIBLE BUT UNPROVEN", "UNLIKELY", "NONSENSE".
{json_instructions}
Claim: "{claim}"
'''
}

# ---- Core Service Functions ----
# (call_openrouter, extract_article_from_url, fetch_crossref, fetch_core, etc. remain the same)
def call_openrouter(prompt, stream=False, temperature=0.2):
    """Calls the OpenRouter API, supports streaming."""
    if not OPENROUTER_API_KEY:
        raise Exception("OPENROUTER_API_KEY is not set in environment variables.")
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": "mistralai/mistral-7b-instruct:free", "messages": [{"role": "user", "content": prompt}], "stream": stream, "temperature": temperature}
    try:
        response = requests.post(OR_URL, headers=headers, json=payload, stream=stream, timeout=90)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        logging.error(f"OpenRouter API call failed: {e}")
        raise Exception(f"API Error or connection issue: {e}") from e

def generate_questions_for_claim(claim):
    """Generates up to 3 research questions for a claim."""
    prompt = f"For the following claim, propose up to 3 concise research questions. Only list the questions.\n\nClaim: {claim}"
    try:
        res = call_openrouter(prompt, temperature=0.5)
        res.raise_for_status()
        content = res.json()["choices"][0]["message"]["content"]
        questions = [q.strip("-•* ") for q in content.splitlines() if q.strip() and len(q.strip()) > 5]
        return questions[:3]
    except Exception as e:
        logging.error(f"Failed to generate questions for claim '{claim}': {e}")
        return []

# ---- Application Routes ----
@app.route("/")
def home_redirect():
    return redirect(url_for('analyze_page'))

@app.route("/analyze")
def analyze_page():
    return render_template("index.html", prefill_claim=request.args.get("claim", ""))

@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.json
    text, mode, use_papers = data.get("text"), data.get("mode"), data.get("usePapers", False)
    if not text or not mode:
        return jsonify({"error": "Missing text or analysis mode."}), 400

    analysis_id = str(uuid.uuid4())
    session['current_analysis_id'] = analysis_id

    extraction_prompt = extraction_templates[mode].format(text=text)
    try:
        res = call_openrouter(extraction_prompt)
        raw_claims = res.json()["choices"][0]["message"]["content"]

        if "No explicit claims found" in raw_claims or not raw_claims.strip():
            return jsonify({"claims": [], "claim_ids": []})

        claims_list = [re.sub(r'^\d+\.\s*', '', line).strip() for line in raw_claims.splitlines() if line.strip() and re.match(r'^\d+\.', line.strip())]

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO analyses (id, text, mode, use_papers) VALUES (?, ?, ?, ?)",
                       (analysis_id, text, mode, 1 if use_papers else 0))

        claim_ids = []
        for claim_text in claims_list:
            cursor.execute("INSERT INTO claims (analysis_id, claim_text, reports_json) VALUES (?, ?, ?)",
                           (analysis_id, claim_text, json.dumps({})))
            claim_ids.append(cursor.lastrowid)

        conn.commit()
        conn.close()

        return jsonify({"claims": claims_list, "claim_ids": claim_ids})
    except Exception as e:
        logging.error(f"Failed to extract claims: {e}")
        return jsonify({"error": f"Failed to extract claims: {str(e)}"}), 500

@app.route("/api/get-claim-details", methods=["POST"])
def get_claim_details():
    claim_id = request.json.get("claim_id")
    analysis_id = session.get('current_analysis_id')
    if not analysis_id or not claim_id:
        return jsonify({"error": "Analysis context or claim ID missing."}), 400

    conn = get_db_connection()
    claim_row = conn.execute("SELECT * FROM claims WHERE id = ? AND analysis_id = ?", (claim_id, analysis_id)).fetchone()
    analysis_row = conn.execute("SELECT mode FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
    conn.close()

    if not claim_row or not analysis_row:
        return jsonify({"error": "Invalid claim or analysis ID."}), 400

    claim_text = claim_row['claim_text']
    current_mode = analysis_row['mode']

    # --- CORRECTED CODE ---
    # The formatting now happens here, when both `claim` and `json_instructions` are available.
    verdict_prompt_template = verification_prompts[current_mode]
    verdict_prompt = verdict_prompt_template.format(
        json_instructions=BASE_VERIFICATION_JSON_INSTRUCTIONS,
        claim=claim_text
    )

    try:
        logging.info(f"Getting model verdict for claim ID {claim_id}...")
        res = call_openrouter(verdict_prompt)
        raw_content = res.json()["choices"][0]["message"]["content"]

        json_str = raw_content.strip().replace("```json", "").replace("```", "").strip()
        model_data = json.loads(json_str)

        questions = generate_questions_for_claim(claim_text)

        conn = get_db_connection()
        conn.execute("UPDATE claims SET model_verdict_json = ?, questions_json = ?, search_keywords_json = ? WHERE id = ?",
                     (json.dumps(model_data), json.dumps(questions), json.dumps(model_data.get("keywords", [])), claim_id))
        conn.commit()
        conn.close()

        return jsonify({
            "model_verdict_json": model_data,
            "questions": questions
        })

    except json.JSONDecodeError:
        logging.error(f"Failed to parse JSON from LLM for claim '{claim_text}'. Raw response: {raw_content}")
        return jsonify({"error": "Model returned invalid format. Could not parse details."}), 500
    except Exception as e:
        logging.error(f"Failed to process claim details for claim '{claim_text}': {e}")
        return jsonify({"error": f"Could not generate model verdict: {str(e)}"}), 500

# (The rest of the file: /api/verify-external, /api/generate-report, /export-pdf, etc., can remain as they were in the previous update, as they were not the source of the error)

if __name__ == "__main__":
    app.run(debug=True)

