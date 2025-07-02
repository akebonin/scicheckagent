from flask import Flask, request, render_template, send_file, Response, session, jsonify
from dotenv import load_dotenv
import os
import requests
import trafilatura
import io
import json
from urllib.parse import quote_plus
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.units import inch
from reportlab.lib import colors # Import colors for ParagraphStyle
import time
import logging
import re # Import regex for link processing in PDF
import uuid # For generating unique IDs for the server-side cache

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv(dotenv_path="/home/scicheckagent/mysite/.env") # Adjust path if needed

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")
if not app.secret_key:
    # Use a dummy key for local testing if not set, but warn
    app.secret_key = os.urandom(24)
    logging.warning("FLASK_SECRET_KEY not set. Using a random key for development. Set a strong key in production!")

# --- Server-Side Global Cache ---
# This dictionary stores large data associated with active sessions to prevent cookie overflow.
# Data here is transient and will be lost on server restarts.
global_app_cache = {}

# API Configuration
OR_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# --- PROMPT TEMPLATES ---
extraction_templates = {
    "General Analysis of Testable Claims": '''
You will be given a text. Extract a **numbered list** of explicit, scientifically testable claims.
**Strict rules:**
- ONLY include claims that appear EXPLICITLY in the text.
- Each claim must be explicitly stated.
- If no explicit, complete, testable claims exist, output exactly: "No explicit claims found."
- Absolutely DO NOT infer, paraphrase, generalize, or introduce external knowledge.
- NEVER include incomplete sentences, headings, summaries, conclusions, speculations, questions, or introductory remarks.
- Output ONLY the claims formatted as a numbered list, or "No explicit claims found."
TEXT:
{text}
OUTPUT:
''',
    "Specific Focus on Scientific Claims": '''
You will be given a text. Extract a **numbered list** of explicit, scientifically testable claims related to science.
**Strict rules:**
- ONLY include claims that appear EXPLICITLY in the text.
- Each claim must be explicitly stated.
- If no relevant testable claims exist, output exactly: "No explicit claims found."
- Absolutely DO NOT infer, paraphrase, generalize, or introduce external knowledge.
- NEVER include incomplete sentences, headings, summaries, conclusions, speculations, questions, or introductory remarks.
TEXT:
{text}
OUTPUT:
''',
    "Technology-Focused Extraction": '''
You will be given a text. Extract a **numbered list** of explicit, testable claims related to technology.
**Strict rules:**
- ONLY include claims that appear EXPLICITLY in the text.
- Each claim must be explicitly stated.
- If no relevant testable claims exist, output exactly: "No relevant testable claims exist."
- Absolutely DO NOT infer, paraphrase, generalize, or introduce external knowledge.
- NEVER include incomplete sentences, headings, summaries, conclusions, speculations, questions, or introductory remarks.
TEXT:
{text}
OUTPUT:
'''
}

verification_prompts = {
    "General Analysis of Testable Claims": '''
Assess the scientific accuracy of the following general claim. Provide:
1. A verdict: **VERIFIED**, **PARTIALLY SUPPORTED**, **INCONCLUSIVE**, or **CONTRADICTED**.
2. A concise justification (max 1000 characters).
3. Relevant source links, formatted as full URLs if known.
Claim: "{claim}"
''',
    "Specific Focus on Scientific Claims": '''
Is the following scientific claim supported by current evidence? Provide:
1. A verdict: **SUPPORTED**, **INCONCLUSIVE**, or **NOT SUPPORTED**.
2. A short explanation grounded in existing knowledge.
3. Include 1–2 relevant sources (if available).
Claim: "{claim}"
''',
    "Technology-Focused Extraction": '''
Evaluate the plausibility of this technology-related claim. Provide:
1. A verdict: **FEASIBLE**, **POSSIBLE BUT UNPROVEN**, **UNLIKELY**, or **NONSENSE**.
2. A 2–3 sentence justification.
3. List supporting or contradicting evidence.
Claim: "{claim}"
'''
}

# --- HELPER FUNCTIONS ---

def call_openrouter(prompt, stream=False, temperature=0.2):
    """Calls the OpenRouter API, supports streaming."""
    if not OPENROUTER_API_KEY:
        raise Exception("OPENROUTER_API_KEY is not set in environment variables.")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "mistralai/mistral-7b-instruct:free",
        "messages": [{"role": "user", "content": prompt}],
        "stream": stream,
        "temperature": temperature
    }
    try:
        response = requests.post(OR_URL, headers=headers, json=payload, stream=stream, timeout=90) # Increased timeout
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        logging.error(f"OpenRouter API call failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            raise Exception(f"API Error {e.response.status_code}: {e.response.text}") from e
        raise Exception(f"Network or API connection error: {e}") from e

def extract_article_from_url(url):
    """Fetches and extracts article text from a URL."""
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
            return text if text else ""
        return ""
    except Exception as e:
        logging.error(f"Error extracting article from URL {url}: {e}")
        return ""

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

def fetch_crossref(query):
    url = f"https://api.crossref.org/works?query.title={quote_plus(query)}&rows=3&select=title,URL,author,abstract"
    headers = {"User-Agent": "SciCheckAgent/1.0 (mailto:example@example.com)"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        items = response.json().get("message", {}).get("items", [])
        results = []
        for item in items:
            results.append({
                "title": item.get("title", ["No title"])[0],
                "abstract": item.get("abstract", "Abstract not available"),
                "url": item.get("URL", "")
            })
        return results
    except requests.exceptions.RequestException as e:
        logging.warning(f"CrossRef API call failed for query '{query}': {e}")
        return []

def fetch_core(query):
    url = f"https://core.ac.uk:443/api-v2/search/{quote_plus(query)}?page=1&pageSize=3&metadata=true"
    headers = {"User-Agent": "SciCheckFallback/1.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        results = []
        if "data" in response.json():
            for item in response.json()["data"]:
                results.append({
                    "title": item.get("title", "No title"),
                    "abstract": item.get("description", "No abstract available"),
                    "url": item.get("downloadUrl", item.get("urls", {}).get("fullText", ""))
                })
        return results
    except requests.exceptions.RequestException as e:
        logging.warning(f"CORE API call failed for query '{query}': {e}")
        return []

# --- API ENDPOINTS ---

@app.route("/")
def index():
    """Renders the main page."""
    return render_template("index.html")

@app.route("/api/extract-article", methods=["POST"])
def extract_article():
    """API endpoint to fetch and extract text from a URL."""
    url = request.json.get("url")
    if not url:
        return jsonify({"error": "URL is required."}), 400
    try:
        text = extract_article_from_url(url)
        if not text:
            return jsonify({"error": "Could not extract content from URL. Please ensure it's a valid article page or paste the text manually."}), 404
        
        # Store article text and mode in global_app_cache, storing only ID in session
        article_id = str(uuid.uuid4())
        global_app_cache[article_id] = {
            "text": text,
            "mode": request.json.get("mode"),
            "claims_data": [] # Initialize claims data structure in cache
        }
        session['current_article_id'] = article_id # Store only the ID in session
        
        return jsonify({"article_text": text})
    except Exception as e:
        logging.error(f"Error in /api/extract-article: {e}")
        return jsonify({"error": f"An error occurred while fetching the URL: {str(e)}"}), 500

@app.route("/api/analyze", methods=["POST"])
def analyze():
    """
    API endpoint to extract claims ONLY.
    Initial model verdict and questions are fetched via a separate endpoint.
    """
    data = request.json
    text = data.get("text")
    mode = data.get("mode")
    use_papers = data.get("usePapers", False) # Default to False if not provided

    if not text or not mode:
        return jsonify({"error": "Missing text or analysis mode."}), 400

    # Generate a unique ID for this analysis session and store large data in cache
    article_id = str(uuid.uuid4())
    global_app_cache[article_id] = {
        "text": text,
        "mode": mode,
        "use_papers": use_papers,
        "claims_data": [] # This will hold claim_text and references to details
    }
    session['current_article_id'] = article_id # Store only this ID in Flask session

    extraction_prompt = extraction_templates[mode].format(text=text)
    try:
        logging.info("Calling OpenRouter for claim extraction...")
        res = call_openrouter(extraction_prompt)
        raw_claims = res.json()["choices"][0]["message"]["content"]
        
        if "No explicit claims found" in raw_claims or not raw_claims.strip():
            # Update cache with empty claims if none found
            global_app_cache[article_id]["claims_data"] = []
            return jsonify({"claims": []})
        
        claims_list = []
        for line in raw_claims.splitlines():
            stripped_line = line.strip()
            if stripped_line and stripped_line[0].isdigit():
                content_start = 0
                while content_start < len(stripped_line) and (stripped_line[content_start].isdigit() or stripped_line[content_start] in ['.', ' ']):
                    content_start += 1
                if content_start < len(stripped_line):
                    claims_list.append(stripped_line[content_start:].strip())
            elif stripped_line:
                 claims_list.append(stripped_line)

        claims_list = [c for c in claims_list if len(c) > 10 and not c.lower().startswith(("output:", "text:", "no explicit claims found"))]

        # Store minimal claim data in the cache's claims_data list
        for claim_text in claims_list:
            global_app_cache[article_id]["claims_data"].append({"text": claim_text})

        # Return just the claims to the frontend
        return jsonify({"claims": claims_list})

    except Exception as e:
        logging.error(f"Failed to extract claims: {e}")
        # Clean up cache entry if analysis fails early
        if article_id in global_app_cache:
            del global_app_cache[article_id]
        if 'current_article_id' in session:
            del session['current_article_id']
        return jsonify({"error": f"Failed to extract claims: {str(e)}"}), 500

@app.route("/api/get-claim-details", methods=["POST"])
def get_claim_details():
    """
    API endpoint to get model verdict and questions for a specific claim.
    Data is retrieved/stored in the server-side cache.
    """
    claim_idx = request.json.get("claim_idx")
    current_article_id = session.get('current_article_id')

    if not current_article_id or current_article_id not in global_app_cache:
        return jsonify({"error": "Analysis context missing. Please re-run analysis."}), 400

    article_cache_data = global_app_cache[current_article_id]
    claims_data_in_cache = article_cache_data.get('claims_data', [])

    if claim_idx is None or claim_idx >= len(claims_data_in_cache):
        return jsonify({"error": "Invalid claim index."}), 400

    claim_item_in_cache = claims_data_in_cache[claim_idx]
    claim_text = claim_item_in_cache['text']
    current_analysis_mode = article_cache_data.get('mode', 'General Analysis of Testable Claims')

    # Check if model_verdict and questions already exist in cache for this claim
    if "model_verdict" in claim_item_in_cache and "questions" in claim_item_in_cache:
        return jsonify({
            "model_verdict": claim_item_in_cache["model_verdict"],
            "questions": claim_item_in_cache["questions"]
        })

    # If not in cache, generate them
    model_verdict = "Could not generate model verdict."
    questions = []

    # Get Model Verdict
    verdict_prompt = verification_prompts[current_analysis_mode].format(claim=claim_text)
    try:
        logging.info(f"Calling OpenRouter for model verdict for claim {claim_idx}...")
        res = call_openrouter(verdict_prompt)
        model_verdict = res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logging.error(f"Failed to get model verdict for claim '{claim_text}': {e}")
        model_verdict = f"Could not generate model verdict: {str(e)}"
    time.sleep(1) # Delay between API calls

    # Generate Questions
    try:
        logging.info(f"Calling OpenRouter for questions for claim {claim_idx}...")
        questions = generate_questions_for_claim(claim_text)
    except Exception as e:
        logging.error(f"Failed to generate questions for claim '{claim_text}': {e}")
        questions = []
    time.sleep(1) # Delay between API calls

    # Store results back in cache for this specific claim
    claim_item_in_cache["model_verdict"] = model_verdict
    claim_item_in_cache["questions"] = questions
    # No need to mark session.modified as we are changing global_app_cache directly

    return jsonify({
        "model_verdict": model_verdict,
        "questions": questions
    })


@app.route("/api/verify-external", methods=["POST"])
def verify_external():
    """API endpoint for external verification using CrossRef and CORE."""
    claim_idx = request.json.get("claim_idx")
    current_article_id = session.get('current_article_id')

    if not current_article_id or current_article_id not in global_app_cache:
        return jsonify({"error": "Analysis context missing. Please re-run analysis."}), 400
    
    article_cache_data = global_app_cache[current_article_id]
    claims_data_in_cache = article_cache_data.get('claims_data', [])
    use_papers = article_cache_data.get('use_papers', False)

    if claim_idx is None or not isinstance(claim_idx, int) or claim_idx >= len(claims_data_in_cache):
        return jsonify({"error": "Invalid claim index or analysis data missing."}), 400

    claim_data_in_cache = claims_data_in_cache[claim_idx]
    claim_text = claim_data_in_cache['text']

    # Check if external verdict and sources already exist in cache
    if "external_verdict" in claim_data_in_cache and "sources" in claim_data_in_cache:
        return jsonify({
            "verdict": claim_data_in_cache["external_verdict"],
            "sources": claim_data_in_cache["sources"]
        })

    sources = []
    external_verdict = "External verification toggled off or no relevant sources found."

    if use_papers:
        logging.info(f"Fetching CrossRef sources for claim {claim_idx}...")
        crossref_sources = fetch_crossref(claim_text)
        time.sleep(0.5) # Delay between external API calls
        logging.info(f"Fetching CORE sources for claim {claim_idx}...")
        core_sources = fetch_core(claim_text)
        time.sleep(0.5)

        sources = crossref_sources + core_sources
        # Remove duplicates based on URL
        seen_urls = set()
        unique_sources = []
        for s in sources:
            if s.get('url') and s['url'] not in seen_urls:
                unique_sources.append(s)
                seen_urls.add(s['url'])
        sources = unique_sources
        
        if sources:
            abstracts_and_titles = "\n\n".join(f"Title: {s['title']}\nAbstract: {s['abstract']}" for s in sources if s.get('abstract'))
            if not abstracts_and_titles:
                 abstracts_and_titles = "\n\n".join(f"Title: {s['title']}" for s in sources)

            prompt = f'''
You are an AI assistant evaluating a claim based on provided scientific paper titles and abstracts.

Claim to evaluate: "{claim_text}"

Available Paper Information:
{abstracts_and_titles}

Based on this information, provide:
1. A verdict: **VERIFIED**, **PARTIALLY SUPPORTED**, **INCONCLUSIVE**, or **CONTRADICTED**.
2. A concise justification (max 500 characters) explaining how the provided papers relate to the claim.
3. Reference relevant paper titles in your justification.
'''
            try:
                logging.info(f"Calling OpenRouter for external verdict for claim {claim_idx}...")
                verdict_res = call_openrouter(prompt)
                external_verdict = verdict_res.json()["choices"][0]["message"]["content"]
            except Exception as e:
                logging.error(f"Failed to generate external verdict for claim '{claim_text}': {e}")
                external_verdict = f"Could not generate external verdict: {str(e)}"
            time.sleep(1) # Delay after OpenRouter call
        else:
            external_verdict = "No relevant scientific papers found for this claim."
    
    # Update cache with external verdict and sources
    claim_data_in_cache["external_verdict"] = external_verdict
    claim_data_in_cache["sources"] = sources

    return jsonify({"verdict": external_verdict, "sources": sources})


@app.route("/api/generate-report", methods=["POST"])
def generate_report():
    """API endpoint to generate and stream the research report.
    Data is retrieved/stored in the server-side cache.
    """
    claim_idx = request.json.get("claim_idx")
    question_idx = request.json.get("question_idx")
    current_article_id = session.get('current_article_id')

    if not current_article_id or current_article_id not in global_app_cache:
        return Response(json.dumps({"error": "Analysis context missing. Please re-run analysis."}), mimetype='text/event-stream', status=400)

    article_cache_data = global_app_cache[current_article_id]
    article_text = article_cache_data.get('text', '')
    claims_data_in_cache = article_cache_data.get('claims_data', [])

    if claim_idx is None or question_idx is None or \
       claim_idx >= len(claims_data_in_cache) or \
       'questions' not in claims_data_in_cache[claim_idx] or \
       question_idx >= len(claims_data_in_cache[claim_idx]['questions']):
        return Response(json.dumps({"error": "Invalid indices or analysis data missing."}), mimetype='text/event-stream', status=404)

    claim_data_in_cache = claims_data_in_cache[claim_idx]
    claim_text = claim_data_in_cache['text']
    question_text = claim_data_in_cache['questions'][question_idx]

    report_key = f"q{question_idx}_report" # Key to store report in claim_data_in_cache
    
    # Check if report already exists in cache for this question
    if report_key in claim_data_in_cache and claim_data_in_cache[report_key]:
        def stream_cached_report():
            yield f"data: {json.dumps({'content': claim_data_in_cache[report_key]})}\n\n"
            yield f"data: [DONE]\n\n"
        return Response(stream_cached_report(), mimetype='text/event-stream')

    prompt = f'''
You are an AI researcher writing a short, evidence-based report (maximum 500 words). Your task is to investigate the research question in relation to the claim using verifiable scientific knowledge. Use the article context to ground your analysis where helpful. Clearly explain how the answer to the research question supports, contradicts, or contextualizes the claim. Provide concise reasoning and avoid speculation.

**Structure:**
1.  **Introduction:** Briefly state the question's relevance to the claim.
2.  **Analysis:** Answer the research question directly, citing evidence or established principles.
3.  **Conclusion:** Summarize how the analysis impacts the validity of the original claim.
4.  **Sources:** List up to 3 relevant sources with clickable full URLs. Prefer recent, peer-reviewed sources.

---
**Article Context:**
{article_text}

**Claim:**
{claim_text}

**Research Question:**
{question_text}

---
**AI Research Report**
'''
    def stream_response():
        full_report_content = ""
        try:
            logging.info(f"Calling OpenRouter for report generation for claim {claim_idx}, question {question_idx}...")
            response = call_openrouter(prompt, stream=True)
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
                if chunk:
                    # Handle SSE format: data: {json_payload}\n\n
                    lines = chunk.split('\n')
                    for line in lines:
                        if line.strip().startswith("data:"):
                            data_part = line.strip()[len("data:"):].strip()
                            if data_part == '[DONE]':
                                continue # This will be handled by outer loop break if response ends
                            try:
                                json_data = json.loads(data_part)
                                content = json_data['choices'][0]['delta'].get('content', '')
                                if content:
                                    full_report_content += content
                                    yield f"data: {json.dumps({'content': content})}\n\n"
                                if json_data['choices'][0].get('finish_reason') == 'stop':
                                    # This is where OpenRouter typically signals end of message
                                    break
                            except json.JSONDecodeError:
                                logging.debug(f"Skipping non-JSON data line: {line}")
                                continue
                if response.raw.read(0): # Check if the stream is truly done
                    break

        except Exception as e:
            logging.error(f"Error during report streaming for claim {claim_idx}, question {question_idx}: {e}")
            error_message = f"data: {json.dumps({'error': str(e)})}\n\n"
            yield error_message
        finally:
            # Store the full report content in cache after streaming is complete
            if full_report_content:
                claim_data_in_cache[report_key] = full_report_content
            yield f"data: [DONE]\n\n" # Always send DONE signal at the end

    return Response(stream_response(), mimetype='text/event-stream')


@app.route("/export-pdf", methods=["GET"]) # Changed to GET for simpler link/button click
def export_pdf():
    """Endpoint to generate and send a PDF report."""
    pdf_reports = []
    current_article_id = session.get('current_article_id')

    if not current_article_id or current_article_id not in global_app_cache:
        return "No active analysis session found. Please run an analysis first.", 400
    
    article_cache_data = global_app_cache[current_article_id]
    claims_data_in_cache = article_cache_data.get('claims_data', [])

    if not claims_data_in_cache:
        return "No claims found for this analysis session.", 400

    for claim_idx, claim_item_in_cache in enumerate(claims_data_in_cache):
        # Ensure essential claim details are present
        if "model_verdict" not in claim_item_in_cache or "questions" not in claim_item_in_cache:
            logging.warning(f"Skipping claim {claim_idx} for PDF: missing model verdict or questions in cache.")
            continue

        # Iterate through all questions for the current claim
        for q_idx, question in enumerate(claim_item_in_cache.get('questions', [])):
            report_key = f"q{q_idx}_report"
            # ONLY include a report if it actually exists in the cache
            if report_key in claim_item_in_cache and claim_item_in_cache[report_key]:
                pdf_reports.append({
                    "claim_text": claim_item_in_cache['text'], # Original claim text
                    "model_verdict": claim_item_in_cache['model_verdict'],
                    "external_verdict": claim_item_in_cache.get('external_verdict', 'Not verified externally.'),
                    "sources": claim_item_in_cache.get('sources', []), # External sources from CrossRef/CORE
                    "question": question,
                    "report": claim_item_in_cache[report_key]
                })

    if not pdf_reports:
        return "No complete reports to export. Generate reports for at least one question first by clicking 'Generate Report'.", 400

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    styles = getSampleStyleSheet()
    
    # Define custom styles for PDF
    styles.add(ParagraphStyle(name='ClaimHeading', parent=styles['h2'], fontName='Helvetica-Bold', fontSize=14, spaceAfter=6))
    styles.add(ParagraphStyle(name='SectionHeading', parent=styles['h3'], fontName='Helvetica-Bold', fontSize=12, spaceAfter=4, textColor=colors.darkblue))
    styles.add(ParagraphStyle(name='NormalParagraph', parent=styles['Normal'], fontName='Helvetica', fontSize=10, leading=12, spaceAfter=8))
    styles.add(ParagraphStyle(name='SourceLink', parent=styles['NormalParagraph'], textColor=colors.blue, fontName='Helvetica', fontSize=9, leading=10, spaceAfter=4))
    styles.add(ParagraphStyle(name='ReportBody', parent=styles['NormalParagraph'], fontName='Helvetica', fontSize=10, leading=14, spaceAfter=10))

    y = height - inch # Initial y position from top margin
    p.setFont("Helvetica-Bold", 20)
    p.drawCentredString(width / 2.0, y, "SciCheck AI Analysis Report")
    y -= 40

    for item in pdf_reports:
        # Check for page break
        if y < 1.5 * inch: # If less than 1.5 inch from bottom, start new page
            p.showPage()
            y = height - inch

        # Claim
        y -= 20 # Space before new claim
        p.setFont("Helvetica-Bold", 14)
        y = draw_paragraph(p, f"Claim: {item['claim_text']}", styles['ClaimHeading'], y, width)
        
        y = draw_paragraph(p, f"<b>Model Verdict:</b> {item['model_verdict']}", styles['NormalParagraph'], y, width)
        y = draw_paragraph(p, f"<b>External Verdict:</b> {item['external_verdict']}", styles['NormalParagraph'], y, width)

        if item['sources']:
            y = draw_paragraph(p, "<b>External Sources:</b>", styles['SectionHeading'], y, width)
            for src in item['sources']:
                link_text = f"{src['title']}"
                if src['url']:
                    # Ensure URL is properly escaped for XML/HTML in ReportLab
                    escaped_url = src['url'].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
                    link_text = f'<link href="{escaped_url}">{link_text}</link>'
                y = draw_paragraph(p, f"- {link_text}", styles['SourceLink'], y, width)
        
        # This is where the specific question and its report start
        y = draw_paragraph(p, f"<b>Research Question:</b> {item['question']}", styles['SectionHeading'], y, width)
        
        # AI Research Report
        if item.get('report'):
            y = draw_paragraph(p, "<b>AI Research Report:</b>", styles['SectionHeading'], y, width)
            # Process report content for bolding and links for ReportLab
            report_content_formatted = item['report']
            # Convert markdown bold (**) to HTML <b>
            report_content_formatted = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', report_content_formatted)
            # Convert markdown links to ReportLab <link> tags
            # Ensure URLs are properly escaped for XML/HTML in ReportLab
            report_content_formatted = re.sub(r'\[(.*?)\]\((https?://[^\s\]]+)\)', r'<link href="\2">\1</link>', report_content_formatted)
            # Convert raw URLs into clickable links for ReportLab
            # Ensure URLs are properly escaped for XML/HTML in ReportLab
            report_content_formatted = re.sub(r'(https?://[^\s<>"\'\]]+)', r'<link href="\1">\1</link>', report_content_formatted)

            y = draw_paragraph(p, report_content_formatted, styles['ReportBody'], y, width)
        y -= 20 # Extra space after each full claim analysis (or question analysis if applicable)

    p.save()
    buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name="SciCheck_AI_Report.pdf")

# Helper function for PDF generation to manage text flow and page breaks
def draw_paragraph(pdf_canvas, text_content, style, y_pos, page_width, left_margin=0.75*inch, right_margin=0.75*inch):
    available_width = page_width - left_margin - right_margin
    # Create a Paragraph object
    para = Paragraph(text_content, style)
    # Wrap it to get its height
    w, h = para.wrapOn(pdf_canvas, available_width, 0) # 0 for height means it will calculate
    
    # Check if there's enough space on the current page, if not, create new page
    if y_pos - h < 0.75*inch: # If it overflows into bottom margin
        pdf_canvas.showPage()
        y_pos = A4[1] - 0.75*inch # Reset y to top margin on new page
    
    # Draw the paragraph
    para.drawOn(pdf_canvas, left_margin, y_pos - h)
    
    return y_pos - h - style.spaceAfter # Return new y position


if __name__ == "__main__":
    app.run(debug=True)

