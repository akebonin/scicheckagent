from flask import Flask, request, render_template, send_file, Response, session, jsonify, redirect, url_for
from dotenv import load_dotenv
import os
import requests
import trafilatura  # Not directly used in the current version for extraction, but kept as in original
import io
import json
from urllib.parse import quote_plus
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import logging
import re
import uuid
import time
from bs4 import BeautifulSoup  # Import BeautifulSoup for URL content extraction
import sqlite3
from datetime import datetime, timedelta
import base64
from PIL import Image
import pytesseract
from openai import OpenAI
from moviepy.editor import VideoFileClip
import yt_dlp
import unicodedata
import html
import hashlib

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

# Database setup for session storage
def init_db():
    conn = sqlite3.connect('/home/scicheckagent/mysite/sessions.db')
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS analysis_sessions (
        session_id TEXT PRIMARY KEY,
        article_data TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    c.execute('''
    CREATE TABLE IF NOT EXISTS media_cache (
        file_hash TEXT PRIMARY KEY,
        media_type TEXT NOT NULL,
        extracted_text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    c.execute('''
    CREATE TABLE IF NOT EXISTS external_sources_cache (
        cache_key TEXT PRIMARY KEY,
        sources_data TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()

def store_analysis(session_id, article_data):
    conn = sqlite3.connect('/home/scicheckagent/mysite/sessions.db')
    c = conn.cursor()
    c.execute('''
    INSERT OR REPLACE INTO analysis_sessions
    (session_id, article_data, last_accessed)
    VALUES (?, ?, ?)
    ''', (session_id, json.dumps(article_data), datetime.now()))
    conn.commit()
    conn.close()

def get_analysis(session_id):
    conn = sqlite3.connect('/home/scicheckagent/mysite/sessions.db')
    c = conn.cursor()
    c.execute('''
    SELECT article_data FROM analysis_sessions
    WHERE session_id = ? AND last_accessed > ?
    ''', (session_id, datetime.now() - timedelta(hours=24)))
    result = c.fetchone()
    conn.close()
    return json.loads(result[0]) if result else None

def update_access_time(session_id):
    conn = sqlite3.connect('/home/scicheckagent/mysite/sessions.db')
    c = conn.cursor()
    c.execute('''
    UPDATE analysis_sessions SET last_accessed = ?
    WHERE session_id = ?
    ''', (datetime.now(), session_id))
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# API Configuration
OR_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
WHISPER_API_KEY = os.getenv("WHISPER_API_KEY")
if not WHISPER_API_KEY:
    logging.error("WHISPER_API_KEY not set.")
    raise ValueError("WHISPER_API_KEY is not set in environment variables.")

# Base prompt templates for consolidation
BASE_EXTRACTION_RULES = '''
**Strict rules:**
- ONLY include claims that appear EXPLICITLY in the text.
- Each claim must be explicitly stated.
- If no explicit, complete, testable claims exist, output exactly: "No explicit claims found."
- Absolutely DO NOT infer, paraphrase, generalize, or introduce external knowledge.
- NEVER include incomplete sentences, headings, summaries, conclusions, speculations, questions, or introductory remarks.
- Output ONLY the claims formatted as a numbered list, or "No explicit claims found."
'''

BASE_JSON_STRUCTURE = '''
Output a structured text response with the following format. Do NOT use code fences (```), JSON, or extra text outside this structure. Use exact labels and colons.

Verdict: VERIFIED
Justification: Concise explanation under 1000 characters.
Sources: None
Keywords: term1, term2, term3, term4, term5

STRICT RULES:
- Verdict: Exactly one of VERIFIED, PARTIALLY_SUPPORTED, INCONCLUSIVE, CONTRADICTED, SUPPORTED, NOT_SUPPORTED, FEASIBLE, POSSIBLE_BUT_UNPROVEN, UNLIKELY, NONSENSE
- Justification: String, max 1000 characters
- Sources: 0-2 valid URLs, comma-separated, or "None" if none
- Keywords: 3-5 scientific/technical terms, comma-separated, each 3-20 characters
- Output ONLY the structured text, nothing else
'''

# Prompt templates
extraction_templates = {
    "General Analysis of Testable Claims": f'''
You will be given a text. Extract a **numbered list** of explicit, scientifically testable claims.

{BASE_EXTRACTION_RULES}

TEXT:

{{text}}

OUTPUT:
''',
    "Specific Focus on Scientific Claims": f'''
You will be given a text. Extract a **numbered list** of explicit, scientifically testable claims related to science.

{BASE_EXTRACTION_RULES}

TEXT:

{{text}}

OUTPUT:
''',
    "Technology-Focused Extraction": f'''
You will be given a text. Extract a **numbered list** of explicit, testable claims related to technology.

{BASE_EXTRACTION_RULES}

TEXT:

{{text}}

OUTPUT:
'''
}

verification_prompts = {
    "General Analysis of Testable Claims": f'''
Analyze this claim and return a structured text response. {BASE_JSON_STRUCTURE}

Claim: "{{claim}}"
''',
    "Specific Focus on Scientific Claims": f'''
Analyze this scientific claim and return a structured text response. {BASE_JSON_STRUCTURE}

Claim: "{{claim}}"
''',
    "Technology-Focused Extraction": f'''
Evaluate this technology claim and return a structured text response. {BASE_JSON_STRUCTURE}

Claim: "{{claim}}"
'''
}

# Helper functions

def compute_file_hash(file_path):
    """Compute SHA256 hash of a file"""
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def compute_content_hash(content):
    """Compute SHA256 hash of text content"""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def get_cached_media(file_hash):
    """Get cached media extraction result"""
    conn = sqlite3.connect('/home/scicheckagent/mysite/sessions.db')
    c = conn.cursor()
    c.execute('SELECT extracted_text FROM media_cache WHERE file_hash = ?', (file_hash,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def store_media_cache(file_hash, media_type, extracted_text):
    """Store media extraction result in cache"""
    conn = sqlite3.connect('/home/scicheckagent/mysite/sessions.db')
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO media_cache (file_hash, media_type, extracted_text)
        VALUES (?, ?, ?)
    ''', (file_hash, media_type, extracted_text))
    conn.commit()
    conn.close()

def get_cached_external_sources(cache_key):
    """Get cached external sources"""
    conn = sqlite3.connect('/home/scicheckagent/mysite/sessions.db')
    c = conn.cursor()
    c.execute('SELECT sources_data FROM external_sources_cache WHERE cache_key = ?', (cache_key,))
    result = c.fetchone()
    conn.close()
    return json.loads(result[0]) if result else None

def store_external_sources_cache(cache_key, sources_data):
    """Store external sources in cache"""
    conn = sqlite3.connect('/home/scicheckagent/mysite/sessions.db')
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO external_sources_cache (cache_key, sources_data)
        VALUES (?, ?)
    ''', (cache_key, json.dumps(sources_data)))
    conn.commit()
    conn.close()
    
def call_openrouter(prompt, stream=False, temperature=0.0, json_mode=False):
    """Calls the OpenRouter API, supports streaming and JSON mode."""
    if not OPENROUTER_API_KEY:
        raise Exception("OPENROUTER_API_KEY is not set in environment variables.")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "google/gemini-2.0-flash-exp:free",
        "messages": [{"role": "user", "content": prompt}],
        "stream": stream,
        "temperature": temperature
    }

    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    try:
        logging.info(f"OpenRouter request payload: {json.dumps(payload, indent=2)}")
        response = requests.post(OR_URL, headers=headers, json=payload, stream=stream, timeout=90)
        response.raise_for_status()
        logging.info(f"OpenRouter response status: {response.status_code}")
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
                if len(current_text) > 200:  # If we get significant content, use it
                    logging.info(f"BeautifulSoup extracted {len(current_text)} characters using selector: {selector}")
                    return current_text
                elif len(current_text) > len(text):  # Keep the longest text found so far
                    text = current_text

        # Fallback if specific selectors didn't yield much
        if len(text) > 50:  # If some text was found by more specific selectors, return it
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
        return ""  # Return empty string if no significant content could be extracted

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

def fetch_semantic_scholar(keywords, max_results=3):
    """Fetch research papers from Semantic Scholar API"""
    SEMANTIC_SCHOLAR_API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY")

    if not SEMANTIC_SCHOLAR_API_KEY:
        logging.warning("SEMANTIC_SCHOLAR_API_KEY not set")
        return []

    # Join keywords for search - Semantic Scholar handles natural language well
    search_query = ' '.join(keywords)

    headers = {
        "x-api-key": SEMANTIC_SCHOLAR_API_KEY,
        "User-Agent": "SciCheckAgent/1.0 (mailto:alizgravenil@gmail.com)"
    }

    params = {
        "query": search_query,
        "limit": max_results,
        "fields": "title,abstract,url,authors,year,citationCount,venue,publicationTypes,externalIds"
    }

    try:
        response = requests.get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            headers=headers,
            params=params,
            timeout=10
        )

        if response.status_code == 429:
            logging.warning("Semantic Scholar rate limit exceeded")
            return []

        response.raise_for_status()

        data = response.json()
        results = []

        if "data" in data and data["data"]:
            for paper in data["data"]:
                # Get authors as string
                authors_list = []
                if paper.get("authors"):
                    authors_list = [author.get("name", "") for author in paper["authors"]]
                authors_str = ", ".join(authors_list[:3])  # First 3 authors
                if len(authors_list) > 3:
                    authors_str += " et al."

                # Construct URL - prefer Semantic Scholar URL, fallback to other IDs
                paper_url = paper.get("url", "")
                if not paper_url and paper.get("externalIds", {}).get("DOI"):
                    paper_url = f"https://doi.org/{paper['externalIds']['DOI']}"
                elif not paper_url and paper.get("externalIds", {}).get("ArXiv"):
                    paper_url = f"https://arxiv.org/abs/{paper['externalIds']['ArXiv']}"

                result = {
                    "title": paper.get("title", "No title"),
                    "abstract": paper.get("abstract", "Abstract not available"),
                    "url": paper_url,
                    "authors": authors_str,
                    "year": paper.get("year", ""),
                    "citation_count": paper.get("citationCount", 0),
                    "venue": paper.get("venue", ""),
                    "publication_types": paper.get("publicationTypes", []),
                    "source": "Semantic Scholar"
                }
                results.append(result)

        logging.info(f"Semantic Scholar found {len(results)} papers for query: {search_query}")
        return results

    except requests.exceptions.RequestException as e:
        logging.warning(f"Semantic Scholar API call failed for query '{search_query}': {e}")
        return []
    except Exception as e:
        logging.warning(f"Unexpected error in Semantic Scholar search: {e}")
        return []

def fetch_pubmed(keywords):
    """Fetch medical literature from PubMed"""
    if not keywords:
        return []

    search_query = '+'.join(keywords)
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={search_query}&retmode=json&retmax=3"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        id_list = data.get('esearchresult', {}).get('idlist', [])
        if not id_list:
            return []

        # Fetch details for the articles
        details_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={','.join(id_list)}&retmode=json"
        details_response = requests.get(details_url, timeout=10)
        details_data = details_response.json()
        results = []
        for pubmed_id in id_list:
            article_data = details_data.get('result', {}).get(pubmed_id, {})
            results.append({
                "title": article_data.get('title', 'No title'),
                "abstract": article_data.get('abstract', 'Abstract not available'),
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pubmed_id}/"
            })
        return results
    except Exception as e:
        logging.warning(f"PubMed API call failed: {e}")
        return []

def analyze_image_with_ocr(image_path):
    """Extract text from image using OCR"""
    try:
        # Use Tesseract OCR to extract text from image
        extracted_text = pytesseract.image_to_string(Image.open(image_path))
        return extracted_text.strip()
    except Exception as e:
        logging.error(f"OCR processing failed: {e}")
        return ""

def transcribe_video(video_path, max_retries=5, retry_delay=5):
    """Transcribe uploaded video using Whisper API"""
    try:
        # Load API key
        WHISPER_API_KEY = os.getenv("WHISPER_API_KEY")
        if not WHISPER_API_KEY:
            logging.error("WHISPER_API_KEY not set.")
            raise ValueError("WHISPER_API_KEY is not set in environment variables.")

        # Extract audio from video
        audio_path = video_path + ".mp3"
        video_clip = VideoFileClip(video_path)
        video_clip.audio.write_audiofile(audio_path)
        video_clip.close()

        # Call Whisper API
        with open(audio_path, "rb") as audio_file:
            files = {"file": audio_file}
            headers = {"X-API-Key": WHISPER_API_KEY}
            data = {
                "format": "text",  # Default format
                "language": "en",  # Default language
                "model_size": "base"  # Default model
            }
            response = requests.post(
                "https://api.whisper-api.com/transcribe",
                files=files,
                headers=headers,
                data=data,
                timeout=120
            )

        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "pending":
                # Handle asynchronous response
                task_id = result.get("task_id")
                if not task_id:
                    raise ValueError("No task_id returned for pending transcription")
                logging.info(f"Transcription pending, task_id: {task_id}")
                return poll_transcription_status(task_id, WHISPER_API_KEY, max_retries, retry_delay)
            transcription = result.get("result", "")
            if not transcription:
                logging.warning("No transcription returned from Whisper API")
                raise ValueError("No transcription returned from Whisper API")
            logging.info(f"Video transcribed successfully: {video_path}")
            return transcription
        else:
            logging.error(f"Whisper API error: {response.status_code} - {response.text}")
            raise ValueError(f"Whisper API error: {response.status_code} - {response.text}")

    except requests.exceptions.RequestException as e:
        logging.error(f"Network error calling Whisper API: {e}")
        raise ValueError(f"Network error: Failed to connect to transcription service")
    except Exception as e:
        logging.error(f"Transcription failed: {e}")
        if os.path.exists(audio_path):
            os.remove(audio_path)
        raise ValueError(f"Failed to transcribe video: {str(e)}")
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)

def transcribe_from_url(video_url, max_retries=5, retry_delay=5):
    """Transcribe video URL using Whisper API"""
    try:
        # Load API key
        WHISPER_API_KEY = os.getenv("WHISPER_API_KEY")
        if not WHISPER_API_KEY:
            logging.error("WHISPER_API_KEY not set.")
            raise ValueError("WHISPER_API_KEY is not set in environment variables.")

        # Download audio using yt-dlp
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': '/tmp/%(id)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            audio_path = ydl.prepare_filename(info).rsplit('.', 1)[0] + '.mp3'

        # Call Whisper API
        with open(audio_path, "rb") as audio_file:
            files = {"file": audio_file}
            headers = {"X-API-Key": WHISPER_API_KEY}
            data = {
                "format": "text",
                "language": "en",
                "model_size": "base"
            }
            response = requests.post(
                "https://api.whisper-api.com/transcribe",
                files=files,
                headers=headers,
                data=data,
                timeout=120
            )

        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "pending":
                # Handle asynchronous response
                task_id = result.get("task_id")
                if not task_id:
                    raise ValueError("No task_id returned for pending transcription")
                logging.info(f"Transcription pending, task_id: {task_id}")
                return poll_transcription_status(task_id, WHISPER_API_KEY, max_retries, retry_delay)
            transcription = result.get("result", "")
            if not transcription:
                logging.warning("No transcription returned from Whisper API")
                raise ValueError("No transcription returned from Whisper API")
            logging.info(f"Video URL transcribed successfully: {video_url}")
            return transcription
        else:
            logging.error(f"Whisper API error: {response.status_code} - {response.text}")
            raise ValueError(f"Whisper API error: {response.status_code} - {response.text}")

    except requests.exceptions.RequestException as e:
        logging.error(f"Network error calling Whisper API: {e}")
        raise ValueError(f"Network error: Failed to connect to transcription service")
    except Exception as e:
        logging.error(f"URL transcription failed: {e}")
        if 'audio_path' in locals() and os.path.exists(audio_path):
            os.remove(audio_path)
        raise ValueError(f"Failed to transcribe video URL: {str(e)}")
    finally:
        if 'audio_path' in locals() and os.path.exists(audio_path):
            os.remove(audio_path)

def poll_transcription_status(task_id, api_key, max_retries=5, retry_delay=5):
    """Poll Whisper API for transcription status"""
    headers = {"X-API-Key": api_key}
    for attempt in range(max_retries):
        try:
            response = requests.get(
                f"https://api.whisper-api.com/status/{task_id}",
                headers=headers,
                timeout=30
            )
            if response.status_code == 200:
                result = response.json()
                status = result.get("status")
                if status == "completed":
                    transcription = result.get("result", "")
                    if not transcription:
                        logging.warning(f"No transcription returned for task_id: {task_id}")
                        raise ValueError("No transcription returned from Whisper API")
                    logging.info(f"Transcription completed for task_id: {task_id}")
                    return transcription
                elif status == "failed":
                    error = result.get("error", "Unknown error")
                    logging.error(f"Transcription failed for task_id: {task_id}, error: {error}")
                    raise ValueError(f"Transcription failed: {error}")
                else:
                    logging.info(f"Transcription still pending for task_id: {task_id}, attempt {attempt + 1}/{max_retries}")
                    time.sleep(retry_delay)
            else:
                logging.error(f"Status check failed: {response.status_code} - {response.text}")
                raise ValueError(f"Status check failed: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Network error during status check for task_id: {task_id}: {e}")
            if attempt == max_retries - 1:
                raise ValueError(f"Network error during status check: {str(e)}")
            time.sleep(retry_delay)
    raise ValueError(f"Transcription did not complete within {max_retries} attempts")

def save_uploaded_file(file, upload_folder="/home/scicheckagent/mysite/uploads"):
    """Save uploaded file and return path"""
    try:
        os.makedirs(upload_folder, exist_ok=True)
        filename = str(uuid.uuid4()) + "_" + file.filename
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)
        return filepath
    except Exception as e:
        logging.error(f"Error saving uploaded file: {e}")
        return None

def normalize_text_for_pdf(text):
    """Normalize Unicode text for PDF compatibility"""
    if not text:
        return text

    # Normalize Unicode
    normalized = unicodedata.normalize('NFKD', text)

    # Replace problematic characters
    replacements = {
        '–': '-',  # en-dash
        '—': '-',  # em-dash
        'â': '-',
        'â': '-',
        'â': "'",
        'â': '"',
        'â': '"',
        '¯': ' ',
        '­': '',  # soft hyphen
        'Î²': 'beta',
        'Î±': 'alpha',
        'Î³': 'gamma',
        'â': '-',  # common mis-encoding
    }

    for old, new in replacements.items():
        normalized = normalized.replace(old, new)

    return normalized

def convert_markdown_tables_to_simple_text(text):
    """Convert markdown tables to simple text format for PDF"""
    table_pattern = r'(\|.*\|\s*\n\|[-:\s|]+\|\s*\n(?:\|.*\|\s*\n)*)'

    def replace_table(match):
        table_text = match.group(0)
        lines = [line.strip() for line in table_text.split('\n') if line.strip().startswith('|')]

        if len(lines) < 2:
            return table_text

        # Extract cells from each line
        table_data = []
        for line in lines:
            cells = [cell.strip() for cell in line.split('|')[1:-1]]  # Remove empty first/last elements
            table_data.append(cells)

        # Check if second line is a separator
        if all(cell.replace('-', '').replace(':', '').replace(' ', '') == '' for cell in table_data[1]):
            table_data.pop(1)  # Remove separator line

        # Convert to simple text representation
        result = []
        for row in table_data:
            result.append(' | '.join(row))

        return '\n'.join(result) + '\n\n'

    return re.sub(table_pattern, replace_table, text, flags=re.MULTILINE)

def cleanup_old_cache():
    """Clean up old cache entries to prevent database bloat"""
    conn = sqlite3.connect('/home/scicheckagent/mysite/sessions.db')
    c = conn.cursor()
    
    # Clean up media cache older than 7 days
    c.execute('DELETE FROM media_cache WHERE created_at < ?', 
              (datetime.now() - timedelta(days=7),))
    
    # Clean up external sources cache older than 14 days
    c.execute('DELETE FROM external_sources_cache WHERE created_at < ?', 
              (datetime.now() - timedelta(days=14),))
    
    # Clean up analysis sessions older than 3 days (extended from 24 hours)
    c.execute('DELETE FROM analysis_sessions WHERE last_accessed < ?', 
              (datetime.now() - timedelta(days=3),))
    
    conn.commit()
    conn.close()
    logging.info("Cache cleanup completed")

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
    elif shared_title and not shared_url:  # If text and title, but no URL
        prefill_content = f"{shared_title}\n\n{shared_text}"
    # If no text was highlighted/shared, but a URL was shared (e.g., sharing a link directly)
    # Since you want to avoid external fetching, we'll just put the URL itself in the text area.
    elif shared_url:
        prefill_content = f"Shared URL: {shared_url}"
        if shared_title:  # Add title if available with URL
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
    """API endpoint to extract claims ONLY."""
    data = request.json
    text = data.get("text")
    mode = data.get("mode")
    use_papers = data.get("usePapers", False)

    if not text or not mode:
        return jsonify({"error": "Missing text or analysis mode."}), 400

    article_id = str(uuid.uuid4())
    session_data = {
        "text": text,
        "mode": mode,
        "use_papers": use_papers,
        "claims_data": []
    }
    store_analysis(article_id, session_data)
    session['current_article_id'] = article_id

    extraction_prompt = extraction_templates[mode].format(text=text)
    try:
        logging.info("Calling OpenRouter for claim extraction...")
        res = call_openrouter(extraction_prompt)
        raw_claims = res.json()["choices"][0]["message"]["content"]

        if "No explicit claims found" in raw_claims or not raw_claims.strip():
            session_data["claims_data"] = []
            store_analysis(article_id, session_data)
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
            session_data["claims_data"].append({"text": claim_text})

        store_analysis(article_id, session_data)
        return jsonify({"claims": claims_list})
    except Exception as e:
        logging.error(f"Failed to extract claims: {e}")
        return jsonify({"error": f"Failed to extract claims: {str(e)}"}), 500

@app.route("/api/get-claim-details", methods=["POST"])
def get_claim_details():
    try:
        claim_idx = request.json.get("claim_idx")
        current_article_id = session.get('current_article_id')

        if not current_article_id:
            return jsonify({"error": "Analysis context missing. Please re-run analysis."}), 400

        # Get data from database
        article_cache_data = get_analysis(current_article_id)
        if not article_cache_data:
            return jsonify({"error": "Analysis session expired or not found."}), 400

        claims_data_in_cache = article_cache_data.get('claims_data', [])
        if claim_idx is None or claim_idx >= len(claims_data_in_cache):
            return jsonify({"error": "Invalid claim index."}), 400

        claim_item_in_cache = claims_data_in_cache[claim_idx]
        claim_text = claim_item_in_cache['text']

        # Safely get the analysis mode with validation
        current_analysis_mode = article_cache_data.get('mode')
        logging.info(f"Current analysis mode: {current_analysis_mode}")

        # Validate the analysis mode
        if not current_analysis_mode or current_analysis_mode not in verification_prompts:
            logging.warning(f"Invalid analysis mode: {current_analysis_mode}. Using default.")
            current_analysis_mode = 'General Analysis of Testable Claims'

        # If already cached, return immediately
        if "model_verdict" in claim_item_in_cache and "questions" in claim_item_in_cache:
            return jsonify({
                "model_verdict": claim_item_in_cache["model_verdict"],
                "questions": claim_item_in_cache["questions"],
                "search_keywords": claim_item_in_cache.get("search_keywords", [])
            })

        # Generate verdict with retry loop
        verdict_prompt = verification_prompts[current_analysis_mode].format(claim=claim_text)
        model_verdict_content = "Could not generate model verdict."
        questions = []
        search_keywords = []
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                logging.info(f"Calling OpenRouter for model verdict for claim {claim_idx}, attempt {retry_count + 1}...")
                res = call_openrouter(verdict_prompt, json_mode=False, temperature=0.0)
                raw_llm_response = res.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                logging.info(f"Raw LLM Response (full, attempt {retry_count + 1}): {repr(raw_llm_response)}")

                if not raw_llm_response.strip():
                    raise ValueError("Empty response from OpenRouter")

                # Parse text response with regex
                verdict_match = re.search(r'Verdict:\s*(VERIFIED|PARTIALLY_SUPPORTED|INCONCLUSIVE|CONTRADICTED|SUPPORTED|NOT_SUPPORTED|FEASIBLE|POSSIBLE_BUT_UNPROVEN|UNLIKELY|NONSENSE)', raw_llm_response, re.IGNORECASE)
                if not verdict_match:
                    logging.warning(f"Invalid verdict format in attempt {retry_count + 1}, retrying...")
                    retry_count += 1
                    continue

                verdict = verdict_match.group(1).upper()

                justification_match = re.search(r'Justification:\s*([\s\S]{20,1000}?(?=\n\s*(?:Sources|Keywords|$)))', raw_llm_response, re.IGNORECASE | re.DOTALL)
                justification = justification_match.group(1).strip()[:1000] if justification_match else 'Justification could not be parsed from response.'

                sources_match = re.search(r'Sources:\s*([\s\S]*?)(?=\n\s*(?:Keywords|$))', raw_llm_response, re.IGNORECASE | re.DOTALL)
                sources = []
                if sources_match:
                    source_text = sources_match.group(1).strip()
                    sources = re.findall(r'(https?://[^\s,)]+)', source_text)[:2] or ['None']

                keywords_match = re.search(r'Keywords:\s*([\w\s,-]{10,})', raw_llm_response, re.IGNORECASE | re.DOTALL)
                if keywords_match:
                    kw_text = keywords_match.group(1).strip()
                    search_keywords = [kw.strip().lower() for kw in re.split(r'[,;\s]+', kw_text) if len(kw.strip()) > 3][:5]
                else:
                    words = re.findall(r'\b[a-zA-Z]{4,}\b', claim_text.lower())
                    search_keywords = list(set(words[:5])) or [claim_text.lower()[:50]]

                # Format for display
                model_verdict_content = f"Verdict: **{verdict}**\n\nJustification: {justification}"
                if sources and sources != ['None']:
                    model_verdict_content += f"\n\nSources:\n" + "\n".join(f"- {src}" for src in sources)

                break  # Successful parse, exit retry loop

            except Exception as e:
                logging.error(f"Failed to process LLM response in attempt {retry_count + 1}: {e}")
                retry_count += 1
                if retry_count == max_retries:
                    model_verdict_content = f"Error generating verdict after {max_retries} attempts: {str(e)}"
                    words = re.findall(r'\b[a-zA-Z]{4,}\b', claim_text.lower())
                    search_keywords = list(set(words[:5])) or [claim_text.lower()[:50]]

        # Generate questions
        try:
            questions = generate_questions_for_claim(claim_text)
        except Exception as e:
            logging.error(f"Failed to generate questions: {e}")
            questions = ["Could not generate research questions"]

        # Store results in database
        claim_item_in_cache["model_verdict"] = model_verdict_content
        claim_item_in_cache["questions"] = questions
        claim_item_in_cache["search_keywords"] = search_keywords

        # Update database
        store_analysis(current_article_id, article_cache_data)
        update_access_time(current_article_id)

        return jsonify({
            "model_verdict": model_verdict_content,
            "questions": questions,
            "search_keywords": search_keywords
        })
    except Exception as e:
        logging.error(f"Error in get_claim_details: {e}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route("/api/verify-external", methods=["POST"])
def verify_external():
    claim_idx = request.json.get("claim_idx")
    current_article_id = session.get('current_article_id')
    
    if not current_article_id:
        return jsonify({"error": "Analysis context missing. Please re-run analysis."}), 400
    
    article_cache_data = get_analysis(current_article_id)
    if not article_cache_data:
        return jsonify({"error": "Analysis session expired or not found."}), 400
    
    claims_data_in_cache = article_cache_data.get('claims_data', [])
    use_papers = article_cache_data.get('use_papers', False)
    
    if claim_idx is None or not isinstance(claim_idx, int) or claim_idx >= len(claims_data_in_cache):
        return jsonify({"error": "Invalid claim index or analysis data missing."}), 400
    
    claim_data_in_cache = claims_data_in_cache[claim_idx]
    claim_text = claim_data_in_cache['text']
    
    # Check if we already have external verification results
    if "external_verdict" in claim_data_in_cache and "sources" in claim_data_in_cache:
        logging.info(f"Using cached external verification for claim {claim_idx}")
        return jsonify({
            "verdict": claim_data_in_cache["external_verdict"],
            "sources": claim_data_in_cache["sources"],
            "cached": True
        })
    
    # Retrieve stored search_keywords from cache for API calls
    search_keywords_for_papers = claim_data_in_cache.get('search_keywords', [claim_text])
    if not search_keywords_for_papers:
        search_keywords_for_papers = [claim_text]
    
    # Create cache key for external sources
    sources_cache_key = compute_content_hash('_'.join(sorted(search_keywords_for_papers)))
    
    sources = []
    external_verdict = "External verification toggled off or no relevant sources found."

    if use_papers:
        # Check cache for external sources
        cached_sources = get_cached_external_sources(sources_cache_key)
        
        if cached_sources:
            logging.info(f"Using cached external sources for keywords: {search_keywords_for_papers}")
            sources = cached_sources
        else:
            # Fetch from multiple sources with rate limiting delays
            all_sources = []

            # 1. Semantic Scholar (primary - most reliable)
            logging.info(f"Fetching Semantic Scholar sources for claim {claim_idx} using keywords: {search_keywords_for_papers}...")
            semantic_sources = fetch_semantic_scholar(search_keywords_for_papers)
            all_sources.extend(semantic_sources)
            time.sleep(1.1)  # Respect 1 request per second rate limit

            # 2. CrossRef
            logging.info(f"Fetching CrossRef sources for claim {claim_idx} using keywords: {search_keywords_for_papers}...")
            crossref_sources = fetch_crossref(search_keywords_for_papers)
            all_sources.extend(crossref_sources)
            time.sleep(0.5)

            # 3. CORE
            logging.info(f"Fetching CORE sources for claim {claim_idx} using keywords: {search_keywords_for_papers}...")
            core_sources = fetch_core(search_keywords_for_papers)
            all_sources.extend(core_sources)
            time.sleep(0.5)

            # 4. PubMed
            logging.info(f"Fetching PubMed sources for claim {claim_idx} using keywords: {search_keywords_for_papers}...")
            pubmed_sources = fetch_pubmed(search_keywords_for_papers)
            all_sources.extend(pubmed_sources)
            time.sleep(0.5)

            # Remove duplicates by URL
            seen_urls = set()
            unique_sources = []
            for s in all_sources:
                url = s.get('url', '')
                if url and url not in seen_urls:
                    unique_sources.append(s)
                    seen_urls.add(url)
            
            sources = unique_sources
            
            # Cache the sources for future use
            if sources:
                store_external_sources_cache(sources_cache_key, sources)

        if sources:
            # Prepare paper information for the LLM
            abstracts_and_titles = "\n\n".join(
                f"Title: {s['title']}\n"
                f"Abstract: {s.get('abstract', 'Abstract not available')}\n"
                f"Authors: {s.get('authors', '')}\n"
                f"Year: {s.get('year', '')}\n"
                f"Citations: {s.get('citation_count', 0)}\n"
                f"Source: {s.get('source', 'Unknown')}"
                for s in sources if s.get('title')
            )

            prompt = f'''
            You are an AI assistant evaluating a claim based on provided scientific paper information.

            Claim to evaluate: "{claim_text}"

            Available Paper Information:

            {abstracts_and_titles}

            Based on this information, provide:

            1. A verdict: **VERIFIED**, **PARTIALLY SUPPORTED**, **INCONCLUSIVE**, **NO RELEVANT PAPERS** or **CONTRADICTED**.

            2. A concise justification (max 1000 characters) explaining how the provided papers do or do not relate to the claim.

            3. Reference relevant paper titles and their key findings in your justification.

            If the provided papers are insufficient or inconclusive for a clear verdict, state "INCONCLUSIVE" and explain why (e.g., "Insufficient relevant information in provided papers" or "Papers don't directly address the specific claim").

            Consider paper credibility factors like citation count, publication venue, and recency.

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
    else:
        external_verdict = "No relevant scientific papers found for this claim."

    # Store results
    claim_data_in_cache["external_verdict"] = external_verdict
    claim_data_in_cache["sources"] = sources

    # Update the session data
    store_analysis(current_article_id, article_cache_data)
    update_access_time(current_article_id)

    return jsonify({
        "verdict": external_verdict, 
        "sources": sources,
        "cached": False
    })


@app.route("/api/process-image", methods=["POST"])
def process_image():
    """Process uploaded image and extract text using OCR with caching"""
    try:
        if 'image' not in request.files:
            return jsonify({"error": "No image file provided"}), 400
        
        image_file = request.files['image']
        if image_file.filename == '':
            return jsonify({"error": "No image file selected"}), 400

        # Save the uploaded image temporarily to compute hash
        image_path = save_uploaded_file(image_file)
        if not image_path:
            return jsonify({"error": "Failed to save image"}), 500

        # Compute file hash and check cache
        file_hash = compute_file_hash(image_path)
        cached_text = get_cached_media(file_hash)
        
        if cached_text:
            logging.info(f"Using cached OCR result for image hash: {file_hash}")
            # Clean up the uploaded file
            try:
                os.remove(image_path)
            except:
                pass
            return jsonify({"extracted_text": cached_text, "cached": True})

        # Extract text using OCR if not cached
        extracted_text = analyze_image_with_ocr(image_path)

        # Store in cache
        if extracted_text:
            store_media_cache(file_hash, 'image', extracted_text)

        # Clean up the uploaded file
        try:
            os.remove(image_path)
        except:
            pass

        if not extracted_text:
            return jsonify({"error": "Could not extract text from image. Please ensure the image contains clear text."}), 400

        return jsonify({"extracted_text": extracted_text, "cached": False})

    except Exception as e:
        logging.error(f"Error in process_image endpoint: {e}")
        return jsonify({"error": f"Failed to process image: {str(e)}"}), 500

@app.route("/api/process-video", methods=["POST"])
def process_video():
    """Process uploaded video and extract transcription using Whisper with caching"""
    try:
        if 'video' not in request.files:
            return jsonify({"error": "No video file provided"}), 400
        
        video_file = request.files['video']
        if video_file.filename == '':
            return jsonify({"error": "No video file selected"}), 400

        # Save the uploaded video temporarily to compute hash
        video_path = save_uploaded_file(video_file)
        if not video_path:
            return jsonify({"error": "Failed to save video"}), 500

        # Compute file hash and check cache
        file_hash = compute_file_hash(video_path)
        cached_transcription = get_cached_media(file_hash)
        
        if cached_transcription:
            logging.info(f"Using cached transcription for video hash: {file_hash}")
            # Clean up the uploaded file
            try:
                os.remove(video_path)
            except:
                pass
            return jsonify({"transcription": cached_transcription, "cached": True})

        # Transcribe video if not cached
        transcription = transcribe_video(video_path)

        # Store in cache
        if transcription:
            store_media_cache(file_hash, 'video', transcription)

        # Clean up the uploaded file
        try:
            os.remove(video_path)
        except:
            pass

        return jsonify({"transcription": transcription, "cached": False})

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        logging.error(f"Error in process_video endpoint: {e}")
        return jsonify({"error": f"Failed to process video: {str(e)}"}), 500

@app.route("/api/transcribe-video-url", methods=["POST"])
def transcribe_video_url():
    """Transcribe video from URL using Whisper."""
    try:
        data = request.json
        video_url = data.get("video_url")
        if not video_url:
            return jsonify({"error": "No video URL provided"}), 400

        transcription = transcribe_from_url(video_url)
        return jsonify({"transcription": transcription})
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        logging.error(f"Error in transcribe_video_url endpoint: {e}")
        return jsonify({"error": f"Failed to transcribe video URL: {str(e)}"}), 500

@app.route("/debug-db")
def debug_db():
    conn = sqlite3.connect('/home/scicheckagent/mysite/sessions.db')
    c = conn.cursor()
    c.execute('SELECT session_id, article_data FROM analysis_sessions ORDER BY last_accessed DESC LIMIT 5')
    results = c.fetchall()
    conn.close()
    debug_info = []
    for session_id, article_data in results:
        try:
            data = json.loads(article_data)
            debug_info.append({
                'session_id': session_id,
                'mode': data.get('mode'),
                'text_preview': data.get('text', '')[:100] + '...' if data.get('text') else None,
                'claims_count': len(data.get('claims_data', []))
            })
        except:
            debug_info.append({'session_id': session_id, 'error': 'Failed to parse'})
    return jsonify(debug_info)

@app.route("/api/generate-report", methods=["POST"])
def generate_report():
    claim_idx = request.json.get("claim_idx")
    question_idx = request.json.get("question_idx")
    current_article_id = session.get('current_article_id')

    if not current_article_id:
        return Response(json.dumps({"error": "Analysis context missing. Please re-run analysis."}), mimetype='application/json', status=400)

    article_cache_data = get_analysis(current_article_id)
    if not article_cache_data:
        return Response(json.dumps({"error": "Analysis session expired or not found."}), mimetype='application/json', status=400)

    article_text = article_cache_data.get('text', '')
    claims_data_in_cache = article_cache_data.get('claims_data', [])

    if claim_idx is None or question_idx is None or claim_idx >= len(claims_data_in_cache) or 'questions' not in claims_data_in_cache[claim_idx] or question_idx >= len(claims_data_in_cache[claim_idx]['questions']):
        return Response(json.dumps({"error": "Invalid indices or analysis data missing."}), mimetype='application/json', status=400)

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
                                    # NORMALIZE UNICODE CHARACTERS
                                    normalized_content = unicodedata.normalize('NFKD', content)
                                    # Replace common problematic characters
                                    normalized_content = normalized_content.replace('–', '-').replace('—', '-')
                                    normalized_content = normalized_content.replace('â', '-').replace('â', '-')
                                    normalized_content = normalized_content.replace('â', "'").replace('â', '"').replace('â', '"')
                                    normalized_content = normalized_content.replace('¯', ' ').replace('­', '')
                                    normalized_content = normalized_content.replace('Î²', 'beta').replace('Î±', 'alpha').replace('Î³', 'gamma')

                                    full_report_content += normalized_content
                                    yield f"data: {json.dumps({'content': normalized_content})}\n\n"

                                if json_data['choices'][0].get('finish_reason') == 'stop':
                                    break
                            except json.JSONDecodeError:
                                logging.debug(f"Skipping non-JSON data line: {line}")
                                continue
            # This check for 'stop' is another way to ensure we break the loop
            # if 'finish_reason' was in the last chunk
            if 'stop' in locals().get('json_data', {}).get('choices', [{}])[0].get('finish_reason', ''):
                pass
        except Exception as e:
            logging.error(f"Error during report streaming for claim {claim_idx}, question {question_idx}: {e}")
            error_message = f"data: {json.dumps({'error': str(e)})}\n\n"
            yield error_message
        finally:
            if full_report_content:
                claim_data_in_cache[report_key] = full_report_content
                # Update the session data
                store_analysis(current_article_id, article_cache_data)
                update_access_time(current_article_id)

        yield f"data: [DONE]\n\n"

    return Response(stream_response(), mimetype='text/event-stream')

# Add this new endpoint to Dsflask_app.py (anywhere after the other API endpoints)

@app.route("/api/available-reports", methods=["GET"])
def get_available_reports():
    """Get list of all available reports for the current session"""
    current_article_id = session.get('current_article_id')

    if not current_article_id:
        return jsonify({"error": "No active analysis session found."}), 400

    article_cache_data = get_analysis(current_article_id)
    if not article_cache_data:
        return jsonify({"error": "Analysis session expired or not found."}), 400

    claims_data_in_cache = article_cache_data.get('claims_data', [])
    available_reports = []

    # Add model verdicts and external verifications
    for claim_idx, claim_data in enumerate(claims_data_in_cache):
        claim_text_preview = claim_data.get('text', '')[:80] + '...' if len(claim_data.get('text', '')) > 80 else claim_data.get('text', '')

        # Add model verdict if available
        if claim_data.get('model_verdict'):
            available_reports.append({
                "id": f"claim-{claim_idx}-summary",
                "type": f"Claim {claim_idx + 1} - Model Verdict & External Verification",
                "description": f"Model analysis and external sources for: {claim_text_preview}"
            })

        # Add question reports if available
        questions = claim_data.get('questions', [])
        for q_idx, question in enumerate(questions):
            report_key = f"q{q_idx}_report"
            if claim_data.get(report_key):
                available_reports.append({
                    "id": f"claim-{claim_idx}-question-{q_idx}",
                    "type": f"Claim {claim_idx + 1} - Question Report {q_idx + 1}",
                    "description": f"Research report for: {question[:100]}..."
                })

    return jsonify(available_reports)

# Update the existing export-pdf endpoint (replace the entire function)
@app.route("/export-pdf", methods=["POST"])
def export_pdf():
    selected_reports = request.json.get("selected_reports", [])
    current_article_id = session.get('current_article_id')

    if not current_article_id:
        return "No active analysis session found. Please run an analysis first.", 400

    article_cache_data = get_analysis(current_article_id)
    if not article_cache_data:
        return "Analysis session expired or not found.", 400

    claims_data_in_cache = article_cache_data.get('claims_data', [])

    if not claims_data_in_cache:
        return "No claims found for this analysis session.", 400

    pdf_reports = []
    added_ids = set()

    # Process selected reports based on their IDs
    for report_id in selected_reports:
        if report_id in added_ids:
            continue

        # Parse report ID format: "claim-{idx}-summary" or "claim-{idx}-question-{q_idx}"
        if report_id.endswith('-summary'):
            # This is a model verdict + external verification summary
            try:
                claim_idx = int(report_id.split('-')[1])
                claim_data = claims_data_in_cache[claim_idx]

                pdf_reports.append({
                    "id": report_id,
                    "claim_text": claim_data.get('text', f"Claim {claim_idx + 1}"),
                    "model_verdict": claim_data.get('model_verdict', ''),
                    "external_verdict": claim_data.get('external_verdict', 'Not verified externally.'),
                    "sources": claim_data.get('sources', []),
                    "question": "Model verdict + external verification",
                    "report": None
                })
                added_ids.add(report_id)
            except (IndexError, ValueError) as e:
                logging.warning(f"Invalid summary report ID format: {report_id}")
                continue

        elif 'question' in report_id:
            # This is a question report: "claim-{idx}-question-{q_idx}"
            try:
                parts = report_id.split('-')
                claim_idx = int(parts[1])
                q_idx = int(parts[3])
                claim_data = claims_data_in_cache[claim_idx]

                report_key = f"q{q_idx}_report"
                if report_key in claim_data and claim_data[report_key]:
                    pdf_reports.append({
                        "id": report_id,
                        "claim_text": claim_data.get('text', f"Claim {claim_idx + 1}"),
                        "model_verdict": claim_data.get('model_verdict', ''),
                        "external_verdict": claim_data.get('external_verdict', 'Not verified externally.'),
                        "sources": claim_data.get('sources', []),
                        "question": claim_data.get('questions', [''])[q_idx],
                        "report": claim_data[report_key]
                    })
                    added_ids.add(report_id)
            except (IndexError, ValueError) as e:
                logging.warning(f"Invalid question report ID format: {report_id}")
                continue

    if not pdf_reports:
        return "No valid reports selected for export.", 400

    # Continue with the existing PDF generation code...
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

        # Claim heading
        y = draw_paragraph(p, f"Claim: {item['claim_text']}", styles['ClaimHeading'], y, width)

        # Model verdict
        y = draw_paragraph(p, f"<b>Model Verdict:</b> {item.get('model_verdict','')}", styles['NormalParagraph'], y, width)

        # External verdict
        y = draw_paragraph(p, f"<b>External Verdict:</b> {item.get('external_verdict','')}", styles['NormalParagraph'], y, width)

        # Sources (if any)
        if item.get('sources'):
            y = draw_paragraph(p, "<b>External Sources:</b>", styles['SectionHeading'], y, width)
            for src in item.get('sources', []):
                link_text = f"{src.get('title','')}"
                if src.get('url'):
                    escaped_url = src['url'].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
                    link_text = f'<link href="{escaped_url}">{link_text}</link>'
                y = draw_paragraph(p, f"- {link_text}", styles['SourceLink'], y, width)

        # Question heading
        y = draw_paragraph(p, f"<b>Research Question:</b> {item.get('question','')}", styles['SectionHeading'], y, width)

        # Full report if present
        if item.get('report'):
            y = draw_paragraph(p, "<b>AI Research Report:</b>", styles['SectionHeading'], y, width)

            report_content_formatted = normalize_text_for_pdf(item['report'])
            report_content_formatted = convert_markdown_tables_to_simple_text(report_content_formatted)
            report_content_formatted = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', report_content_formatted)
            report_content_formatted = re.sub(r'\[(.*?)\]\((https?://[^\s\]]+)\)', r'<link href="\2">\1</link>', report_content_formatted)

            y = draw_paragraph(p, report_content_formatted, styles['ReportBody'], y, width)

        y -= 20

    p.save()
    buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name="SciCheck_AI_Report.pdf")

def draw_paragraph(pdf_canvas, text_content, style, y_pos, page_width, left_margin=0.75*inch, right_margin=0.75*inch):
    available_width = page_width - left_margin - right_margin

    # NORMALIZE TEXT CONTENT FIRST
    text_content = normalize_text_for_pdf(text_content)

    # Replace markdown newlines with HTML <br/> for ReportLab Paragraph
    text_content = text_content.replace('\n', '<br/>')

    para = Paragraph(text_content, style)
    w, h = para.wrapOn(pdf_canvas, available_width, 0)

    if y_pos - h < 0.75*inch:
        pdf_canvas.showPage()
        y_pos = A4[1] - 0.75*inch

    para.drawOn(pdf_canvas, left_margin, y_pos - h)
    return y_pos - h - style.spaceAfter

if __name__ == "__main__":
    app.run(debug=True)
