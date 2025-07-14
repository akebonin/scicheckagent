from flask import Flask, request, render_template, send_file, Response, session, jsonify, redirect, url_for
from dotenv import load_dotenv
import os
import requests
import trafilatura # Not directly used in the current version for extraction, but kept as in original
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
from bs4 import BeautifulSoup # Import BeautifulSoup for URL content extraction

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
# Ensure this path is correct for your PythonAnywhere setup
load_dotenv(dotenv_path="/home/scicheckagent/mysite/.env")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")
if not app.secret_key:
    app.secret_key = os.urandom(24)
    logging.warning("FLASK_SECRET_KEY not set. Using a random key for development. Set a strong key in production!")

# Server-side global cache
global_app_cache = {}

# API Configuration
OR_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Prompt templates
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

# REVERTED verification_prompts to ensure Section 3 is for sources and Section 4 for keywords.
# Added explicit instructions for source format in Section 3.
verification_prompts = {
    "General Analysis of Testable Claims": '''
Assess the scientific accuracy of the following general claim. Provide:
1. A verdict: **VERIFIED**, **PARTIALLY SUPPORTED**, **INCONCLUSIVE**, or **CONTRADICTED**. Provide exclusively one of the listed verdict options for A Verdict without any additions, details, explanations or conditionalities in brakets, lists, bullet points or any other formats.
2. A concise justification grounded in existing knowledge (max 1000 characters). If you cite a source, embed the full URL directly in the justification.
3. Relevant source links: List 1-2 directly relevant and clickable source URLs (e.g., academic papers, reputable news, institutional reports) that directly support your justification, if not already embedded in section 2. Output "No additional sources provided" if none are directly relevant.
4. Search Keywords: A comma-separated list of 3-5 highly relevant scientific keywords or short phrases for external literature search. Use quotes for multi-word phrases if applicable.

Claim: "{claim}"
''',
    "Specific Focus on Scientific Claims": '''
Is the following scientific claim supported by current evidence? Provide:
1. A verdict: **SUPPORTED**, **INCONCLUSIVE**, or **NOT SUPPORTED**. Provide exclusively one of the listed verdict options for A Verdict without any additions, details, explanations or conditionalities in brakets, lists, bullet points or any other formats.
2. A concise justification grounded in current evidence (max 1000 characters). If you cite a source, embed the full URL directly in the justification.
3. Relevant source links: List 1-2 directly relevant and clickable source URLs (e.g., academic papers, reputable news, institutional reports) that directly support your justification, if not already embedded in section 2. Output "No additional sources provided" if none are directly relevant.
4. Search Keywords: A comma-separated list of 3-5 highly relevant scientific keywords or short phrases for external literature search. Use quotes for multi-word phrases if applicable.

Claim: "{claim}"
''',
    "Technology-Focused Extraction": '''
Evaluate the plausibility of this technology-related claim. Provide:
1. A verdict: **FEASIBLE**, **POSSIBLE BUT UNPROVEN**, **UNLIKELY**, or **NONSENSE**. Provide exclusively one of the listed verdict options for A Verdict without any additions, details, explanations or conditionalities in brakets, lists, bullet points or any other formats.
2. A concise justification grounded in existing knowledge (max 1000 characters). If you cite a source, embed the full URL directly in the justification.
3. Relevant source links: List 1-2 directly relevant and clickable source URLs (e.g., academic papers, reputable news, institutional reports) that directly support your justification, if not already embedded in section 2. Output "No additional sources provided" if none are directly relevant.
4. Search Keywords: A comma-separated list of 3-5 highly relevant technology-related keywords or short phrases for external literature search. Use quotes for multi-word phrases if applicable.

Claim: "{claim}"
'''
}

# Helper functions
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
        response = requests.post(OR_URL, headers=headers, json=payload, stream=stream, timeout=90)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        logging.error(f"OpenRouter API call failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            raise Exception(f"API Error {e.response.status_code}: {e.response.text}") from e
        raise Exception(f"Network or API connection error: {e}") from e

def extract_article_from_url(url):
    """Fetch and extract article content from a URL using direct requests and BeautifulSoup."""
    try:
        headers = {"User-Agent": "SciCheckAgent/1.0 (mailto:alizgravenil@gmail.com)"}
        session = requests.Session()
        logging.info(f"Fetching URL: {url}")
        response = session.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Prioritize common article content selectors
        content_selectors = [
            'article',
            '.article-body-commercial-selector',  # Guardian-specific example
            'main',
            '.article-content',
            '.post-content',
            '.entry-content',
            'div[itemprop="articleBody"]',
            'div[id*="content"]',
            'div[class*="text"]'
        ]

        text = ""
        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                # Concatenate text from all found elements of this selector
                current_text = ' '.join(elem.get_text(separator=' ', strip=True) for elem in elements)
                if len(current_text) > 200: # If we get significant content, use it
                    logging.info(f"BeautifulSoup extracted {len(current_text)} characters using selector: {selector}")
                    return current_text
                elif len(current_text) > len(text): # Keep the longest text found so far
                    text = current_text

        # Fallback if specific selectors didn't yield much
        if len(text) > 50: # If some text was found by more specific selectors, return it
            logging.info(f"Returning partial BeautifulSoup text: {text[:100]}...")
            return text

        logging.info("Falling back to raw HTML body extraction if no specific content found.")
        body = soup.find('body')
        if body:
            # Remove scripts, styles, navs, headers, footers for cleaner text
            for elem in body(['script', 'style', 'nav', 'header', 'footer', 'aside', '.sidebar', '.comments', '#comments']):
                elem.decompose()
            raw_body_text = ' '.join(body.get_text(separator=' ', strip=True).split())
            if len(raw_body_text) > 200:
                logging.info(f"Raw HTML body extraction yielded {len(raw_body_text)} characters.")
                return raw_body_text
            elif len(raw_body_text) > 50:
                logging.info(f"Raw HTML body extraction yielded {len(raw_body_text)} characters (may be short).")
                return raw_body_text

        logging.warning("BeautifulSoup extracted insufficient content from URL.")
        return "" # Return empty string if no significant content could be extracted

    except requests.exceptions.RequestException as e:
        logging.error(f"Network or HTTP error fetching URL {url}: {e}")
        return ""
    except Exception as e:
        logging.error(f"General error extracting article from URL {url}: {e}")
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

# MODIFIED: fetch_crossref now accepts a list of keywords
def fetch_crossref(keywords):
    if not keywords:
        logging.warning("No keywords provided for CrossRef search.")
        return []

    # Join keywords with AND, add quotes for multi-word phrases for better search specificity
    search_query = ' AND '.join([f'"{kw}"' if ' ' in kw else kw for kw in keywords])

    url = f"https://api.crossref.org/works?query={quote_plus(search_query)}&rows=3&select=title,URL,author,abstract"
    headers = {"User-Agent": "SciCheckAgent/1.0 (mailto:alizgravenil@gmail.com)"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        items = response.json().get("message", {}).get("items", [])
        results = []
        for item in items:
            results.append({
                "title": item.get("title", ["No title"])[0] if item.get("title") else "No title",
                "abstract": item.get("abstract", "Abstract not available"),
                "url": item.get("URL", "")
            })
        return results
    except requests.exceptions.RequestException as e:
        logging.warning(f"CrossRef API call failed for query '{search_query}': {e}")
        return []

# MODIFIED: fetch_core now accepts a list of keywords
def fetch_core(keywords):
    if not keywords:
        logging.warning("No keywords provided for CORE search.")
        return []

    # Join keywords with AND, add quotes for multi-word phrases for better search specificity
    search_query = ' AND '.join([f'"{kw}"' if ' ' in kw else kw for kw in keywords])

    url = f"https://core.ac.uk:443/api-v2/search/{quote_plus(search_query)}?page=1&pageSize=3&metadata=true"
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
        logging.warning(f"CORE API call failed for query '{search_query}': {e}")
        return []

# API Endpoints

# Redirect root to /analyze
@app.route("/")
def home_redirect():
    """Redirects the root URL to the /analyze route."""
    return redirect(url_for('analyze_page'))

@app.route("/analyze")
def analyze_page():
    """Renders the main page, optionally pre-filling the claim from query parameters."""
    prefill_claim = request.args.get("claim", "")
    return render_template("index.html", prefill_claim=prefill_claim)

@app.route('/share-target', methods=['POST'])
def share_target():
    shared_text = request.form.get('text', '')
    shared_title = request.form.get('title', '')
    shared_url = request.form.get('url', '')

    prefill_content = ""

    # Prioritize shared text if available
    if shared_text:
        prefill_content = shared_text
        # If there's also a URL, append it to the text for context,
        # but avoid re-adding if the text already contains the URL
        if shared_url and not (shared_url in shared_text or "http" in shared_text or "www" in shared_text):
            prefill_content += f"\n\n(Shared from: {shared_url})"
        elif shared_title and not shared_url: # If text and title, but no URL
             prefill_content = f"{shared_title}\n\n{shared_text}"

    # If no text was highlighted/shared, but a URL was shared (e.g., sharing a link directly)
    # Since you want to avoid external fetching, we'll just put the URL itself in the text area.
    elif shared_url:
        prefill_content = f"Shared URL: {shared_url}"
        if shared_title: # Add title if available with URL
            prefill_content = f"{shared_title}\n\n{prefill_content}"

    # If only a title was shared (less common)
    elif shared_title:
        prefill_content = shared_title

    return render_template('index.html', prefill_claim=prefill_content)

@app.route("/api/extract-article", methods=["POST"])
def extract_article():
    url = request.json.get("url")
    if not url:
        return jsonify({"error": "URL is required."}), 400
    try:
        text = extract_article_from_url(url)
        if not text:
            return jsonify({"error": "Could not extract content from URL. Please ensure it's a valid public webpage or paste the text manually."}), 400
        logging.info(f"Returning article text to client (first 100 chars): {text[:100]}...")
        return jsonify({"article_text": text})
    except Exception as e:
        logging.error(f"Error in extract_article endpoint: {e}")
        return jsonify({"error": f"Failed to fetch article: {str(e)}"}), 400

@app.route("/api/analyze", methods=["POST"])
def analyze():
    """
    API endpoint to extract claims ONLY.
    Initial model verdict and questions are fetched via a separate endpoint.
    """
    data = request.json
    text = data.get("text")
    mode = data.get("mode")
    use_papers = data.get("usePapers", False)
    if not text or not mode:
        return jsonify({"error": "Missing text or analysis mode."}), 400
    article_id = str(uuid.uuid4())
    global_app_cache[article_id] = {
        "text": text,
        "mode": mode,
        "use_papers": use_papers,
        "claims_data": []
    }
    session['current_article_id'] = article_id
    extraction_prompt = extraction_templates[mode].format(text=text)
    try:
        logging.info("Calling OpenRouter for claim extraction...")
        res = call_openrouter(extraction_prompt)
        raw_claims = res.json()["choices"][0]["message"]["content"]
        if "No explicit claims found" in raw_claims or not raw_claims.strip():
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
        for claim_text in claims_list:
            global_app_cache[article_id]["claims_data"].append({"text": claim_text})
        return jsonify({"claims": claims_list})
    except Exception as e:
        logging.error(f"Failed to extract claims: {e}")
        if article_id in global_app_cache:
            del global_app_cache[article_id]
        if 'current_article_id' in session:
            del session['current_article_id']
        return jsonify({"error": f"Failed to extract claims: {str(e)}"}), 500

@app.route("/api/get-claim-details", methods=["POST"])
def get_claim_details():
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

    # If already cached, return immediately
    if "model_verdict" in claim_item_in_cache and \
       "questions" in claim_item_in_cache and \
       "search_keywords" in claim_item_in_cache: # Check for keywords as well
        return jsonify({
            "model_verdict": claim_item_in_cache["model_verdict"],
            "questions": claim_item_in_cache["questions"],
            "search_keywords": claim_item_in_cache.get("search_keywords", [])
        })

    verdict_prompt = verification_prompts[current_analysis_mode].format(claim=claim_text)

    model_verdict_content = "Could not generate model verdict."
    questions = []
    search_keywords = [] # Initialize search_keywords

    try:
        logging.info(f"Calling OpenRouter for model verdict and keywords for claim {claim_idx}...")
        res = call_openrouter(verdict_prompt)
        raw_llm_response = res.json()["choices"][0]["message"]["content"]
        logging.info(f"Raw LLM Response from get_claim_details: \n{raw_llm_response}")

        # Split response by numbered sections to extract keywords specifically
        sections = re.split(r'\n\s*(\d+)\.\s*', raw_llm_response, flags=re.DOTALL)
        parsed_sections_map = {}
        for i in range(1, len(sections), 2):
            try:
                num = int(sections[i].strip())
                content = sections[i+1].strip() if i+1 < len(sections) else ""
                parsed_sections_map[num] = content
            except ValueError:
                logging.warning(f"Could not parse section number from '{sections[i]}'")

        # Store the entire raw LLM response as model_verdict_content
        model_verdict_content = raw_llm_response

        # Extract Search Keywords from section 4
        if 4 in parsed_sections_map:
            temp_keywords_str = parsed_sections_map[4].strip()
            # Remove leading "Search Keywords:"
            temp_keywords_str = re.sub(r'^(Search Keywords:)\s*', '', temp_keywords_str, flags=re.IGNORECASE).strip()

            # Remove outer quotes if the LLM wrapped the entire string in quotes
            if temp_keywords_str.startswith('"') and temp_keywords_str.endswith('"'):
                temp_keywords_str = temp_keywords_str[1:-1]

            # Split by comma and clean each keyword
            search_keywords = [kw.strip().strip('"') for kw in temp_keywords_str.split(',') if kw.strip()]
            if not search_keywords:
                logging.warning("No keywords parsed from section 4. Falling back to original claim text for search.")
                search_keywords = [claim_text] # Default fallback if LLM didn't provide valid keywords
        else:
            logging.warning("Section 4 (Search Keywords) not found in LLM response. Falling back to original claim text for search.")
            search_keywords = [claim_text] # Default fallback

    except Exception as e:
        logging.error(f"Failed to process LLM response for claim '{claim_text}': {e}")
        logging.error(f"Raw LLM Response that caused error: \n{raw_llm_response}")
        model_verdict_content = f"Could not generate model verdict: {str(e)}"
        search_keywords = [claim_text] # Ensure search still works as a fallback

    time.sleep(1) # Add a small delay

    try:
        logging.info(f"Calling OpenRouter for questions for claim {claim_idx}...")
        questions = generate_questions_for_claim(claim_text)
    except Exception as e:
        logging.error(f"Failed to generate questions for claim '{claim_text}': {e}")
        questions = []

    time.sleep(1) # Add a small delay

    # Store data in cache
    claim_item_in_cache["model_verdict"] = model_verdict_content # Store the raw string
    claim_item_in_cache["questions"] = questions
    claim_item_in_cache["search_keywords"] = search_keywords # Store the extracted keywords

    return jsonify({
        "model_verdict": model_verdict_content, # Send the raw string to frontend
        "questions": questions,
        "search_keywords": search_keywords # Send the extracted keywords to frontend
    })

@app.route("/api/verify-external", methods=["POST"])
def verify_external():
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

    # Retrieve stored search_keywords from cache for API calls
    search_keywords_for_papers = claim_data_in_cache.get('search_keywords', [claim_text])
    if not search_keywords_for_papers: # Fallback if for some reason it's empty
        search_keywords_for_papers = [claim_text]

    sources = []
    external_verdict = "External verification toggled off or no relevant sources found."

    if use_papers:
        logging.info(f"Fetching CrossRef sources for claim {claim_idx} using keywords: {search_keywords_for_papers}...")
        crossref_sources = fetch_crossref(search_keywords_for_papers) # Pass keywords list
        time.sleep(0.5)
        logging.info(f"Fetching CORE sources for claim {claim_idx} using keywords: {search_keywords_for_papers}...")
        core_sources = fetch_core(search_keywords_for_papers) # Pass keywords list
        time.sleep(0.5)

        sources = crossref_sources + core_sources
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

            # Use the original claim text for the LLM prompt, but based on filtered search results
            prompt = f'''
You are an AI assistant evaluating a claim based on provided scientific paper titles and abstracts.
Claim to evaluate: "{claim_text}"
Available Paper Information:
{abstracts_and_titles}
Based on this information, provide:
1. A verdict: **VERIFIED**, **PARTIALLY SUPPORTED**, **INCONCLUSIVE**, **NO RELEVANT PAPERS** or **CONTRADICTED**.
2. A concise justification (max 1000 characters) explaining how the provided papers do or do not relate to the claim.
3. Reference relevant paper titles in your justification.
If the provided papers are insufficient or inconclusive for a clear verdict, state "INCONCLUSIVE" and explain why (e.g., "Insufficient relevant information in provided papers").
'''
            try:
                logging.info(f"Calling OpenRouter for external verdict for claim {claim_idx}...")
                verdict_res = call_openrouter(prompt)
                external_verdict = verdict_res.json()["choices"][0]["message"]["content"]
            except Exception as e:
                logging.error(f"Failed to generate external verdict for claim '{claim_text}': {e}")
                external_verdict = f"Could not generate external verdict: {str(e)}"
            time.sleep(1)
        else:
            external_verdict = "No relevant scientific papers found for this claim."

    claim_data_in_cache["external_verdict"] = external_verdict
    claim_data_in_cache["sources"] = sources
    return jsonify({"verdict": external_verdict, "sources": sources})

@app.route("/api/generate-report", methods=["POST"])
def generate_report():
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
        return Response(json.dumps({"error": "Invalid indices or analysis data missing."}), mimetype='text/event-stream', status=400)
    claim_data_in_cache = claims_data_in_cache[claim_idx]
    claim_text = claim_data_in_cache['text']
    question_text = claim_data_in_cache['questions'][question_idx]
    model_verdict_content = claim_data_in_cache.get('model_verdict', 'Verdict not yet generated by AI.')
    external_verdict_content = claim_data_in_cache.get('external_verdict', 'Not yet externally verified.')
    report_key = f"q{question_idx}_report"
    if report_key in claim_data_in_cache and claim_data_in_cache[report_key]:
        def stream_cached_report():
            yield f"data: {json.dumps({'content': claim_data_in_cache[report_key]})}\n\n"
            yield f"data: [DONE]\n\n"
        return Response(stream_cached_report(), mimetype='text/event-stream')
    prompt = f'''
You are an AI researcher writing a short, evidence-based report (maximum 1000 words). Your task is to investigate the research question in relation to the claim using verifiable scientific knowledge. Use the article context to ground your analysis where helpful. Clearly explain how the answer to the research question supports, contradicts, or contextualizes the claim. Provide concise reasoning and avoid speculation.
**Structure:**
1. **Introduction:** Briefly state the question's relevance to the claim.
2. **Analysis:** Answer the research question directly, citing evidence or established principles.
3. **Conclusion:** Summarize how the analysis impacts the validity of the original claim.
4. **Sources:** List up to 3 relevant sources with clickable full URLs. Prefer recent, peer-reviewed sources.
---
**Article Context:**
{article_text}
**Claim:**
{claim_text}
**AI's Initial Verdict on Claim:**
{model_verdict_content}
**External Verification Verdict (if available):**
{external_verdict_content}
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
                    lines = chunk.split('\n')
                    for line in lines:
                        if line.strip().startswith("data:"):
                            data_part = line.strip()[len("data:"):].strip()
                            if data_part == '[DONE]':
                                continue
                            try:
                                json_data = json.loads(data_part)
                                content = json_data['choices'][0]['delta'].get('content', '')
                                if content:
                                    full_report_content += content
                                    yield f"data: {json.dumps({'content': content})}\n\n"
                                if json_data['choices'][0].get('finish_reason') == 'stop':
                                    break
                            except json.JSONDecodeError:
                                logging.debug(f"Skipping non-JSON data line: {line}")
                                continue
                if response.raw.read(0): # Check if the stream is truly empty
                    break
        except Exception as e:
            logging.error(f"Error during report streaming for claim {claim_idx}, question {question_idx}: {e}")
            error_message = f"data: {json.dumps({'error': str(e)})}\n\n"
            yield error_message
        finally:
            if full_report_content:
                claim_data_in_cache[report_key] = full_report_content
            yield f"data: [DONE]\n\n"
    return Response(stream_response(), mimetype='text/event-stream')

@app.route("/export-pdf", methods=["GET"])
def export_pdf():
    pdf_reports = []
    current_article_id = session.get('current_article_id')
    if not current_article_id or current_article_id not in global_app_cache:
        return "No active analysis session found. Please run an analysis first.", 400
    article_cache_data = global_app_cache[current_article_id]
    claims_data_in_cache = article_cache_data.get('claims_data', [])
    if not claims_data_in_cache:
        return "No claims found for this analysis session.", 400
    for claim_idx, claim_item_in_cache in enumerate(claims_data_in_cache):
        # Use 'model_verdict' directly from cache, as it's now the fully formatted string
        if "model_verdict" not in claim_item_in_cache or "questions" not in claim_item_in_cache:
            logging.warning(f"Skipping claim {claim_idx} for PDF: missing model verdict or questions in cache.")
            continue
        for q_idx, question in enumerate(claim_item_in_cache.get('questions', [])):
            report_key = f"q{q_idx}_report"
            if report_key in claim_item_in_cache and claim_item_in_cache[report_key]:
                pdf_reports.append({
                    "claim_text": claim_item_in_cache['text'],
                    "model_verdict": claim_item_in_cache['model_verdict'], # Directly use the formatted string
                    "external_verdict": claim_item_in_cache.get('external_verdict', 'Not verified externally.'),
                    "sources": claim_item_in_cache.get('sources', []),
                    "question": question,
                    "report": claim_item_in_cache[report_key]
                })
    if not pdf_reports:
        return "No complete reports to export. Generate reports for at least one question first by clicking 'Generate Report'.", 400
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='ClaimHeading', parent=styles['h2'], fontName='Helvetica-Bold', fontSize=14, spaceAfter=6))
    styles.add(ParagraphStyle(name='SectionHeading', parent=styles['h3'], fontName='Helvetica-Bold', fontSize=12, spaceAfter=4, textColor=colors.darkblue))
    styles.add(ParagraphStyle(name='NormalParagraph', parent=styles['Normal'], fontName='Helvetica', fontSize=10, leading=12, spaceAfter=8))
    styles.add(ParagraphStyle(name='SourceLink', parent=styles['NormalParagraph'], textColor=colors.blue, fontName='Helvetica', fontSize=9, leading=10, spaceAfter=4))
    styles.add(ParagraphStyle(name='ReportBody', parent=styles['NormalParagraph'], fontName='Helvetica', fontSize=10, leading=14, spaceAfter=10))
    y = height - inch
    p.setFont("Helvetica-Bold", 20)
    p.drawCentredString(width / 2.0, y, "SciCheck AI Analysis Report")
    y -= 40
    for item in pdf_reports:
        if y < 1.5 * inch:
            p.showPage()
            y = height - inch
        y -= 20
        y = draw_paragraph(p, f"Claim: {item['claim_text']}", styles['ClaimHeading'], y, width)
        y = draw_paragraph(p, f"<b>Model Verdict:</b> {item['model_verdict']}", styles['NormalParagraph'], y, width)
        y = draw_paragraph(p, f"<b>External Verdict:</b> {item['external_verdict']}", styles['NormalParagraph'], y, width)
        if item['sources']:
            y = draw_paragraph(p, "<b>External Sources:</b>", styles['SectionHeading'], y, width)
            for src in item['sources']:
                link_text = f"{src['title']}"
                if src['url']:
                    escaped_url = src['url'].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
                    # IMPORTANT: The link href needs to be escaped for PDF generation, but not necessarily for HTML.
                    # The current code uses target="_blank" rel="noopener noreferrer" which is HTML specific.
                    # For PDF, the link creation is different. The reportlab link tag is simple.
                    link_text = f'<link href="{escaped_url}">{link_text}</link>'
                y = draw_paragraph(p, f"- {link_text}", styles['SourceLink'], y, width)
        y = draw_paragraph(p, f"<b>Research Question:</b> {item['question']}", styles['SectionHeading'], y, width)
        if item.get('report'):
            y = draw_paragraph(p, "<b>AI Research Report:</b>", styles['SectionHeading'], y, width)
            report_content_formatted = item['report']
            # Reapply markdown for PDF rendering
            report_content_formatted = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', report_content_formatted)
            report_content_formatted = re.sub(r'\[(.*?)\]\((https?://[^\s\]]+)\)', r'<link href="\2">\1</link>', report_content_formatted)
            y = draw_paragraph(p, report_content_formatted, styles['ReportBody'], y, width)
        y -= 20
    p.save()
    buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name="SciCheck_AI_Report.pdf")

def draw_paragraph(pdf_canvas, text_content, style, y_pos, page_width, left_margin=0.75*inch, right_margin=0.75*inch):
    available_width = page_width - left_margin - right_margin
    para = Paragraph(text_content, style)
    w, h = para.wrapOn(pdf_canvas, available_width, 0)
    if y_pos - h < 0.75*inch:
        pdf_canvas.showPage()
        y_pos = A4[1] - 0.75*inch
    para.drawOn(pdf_canvas, left_margin, y_pos - h)
    return y_pos - h - style.spaceAfter

if __name__ == "__main__":
    app.run(debug=True)
