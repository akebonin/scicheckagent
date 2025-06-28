from flask import Flask, request, jsonify, render_template, Response, session
from dotenv import load_dotenv
import os
import requests
import trafilatura
import bleach
from urllib.parse import urlparse

# Load environment variables and init app
load_dotenv(dotenv_path="/home/scicheckagent/mysite/.env")
app = Flask(__name__)
app.secret_key = os.urandom(24)

# OpenRouter config
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OR_URL = "https://openrouter.ai/api/v1/chat/completions"

# Regular request (non-streaming)
def call_openrouter(system_prompt, user_prompt):
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is missing.")

    messages = session.get('conversation_history', [])
    if not messages:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "mistralai/mistral-7b-instruct:free",
        "messages": messages
    }

    response = requests.post(OR_URL, headers=headers, json=payload)
    response.raise_for_status()
    result = response.json()
    reply = result["choices"][0]["message"]["content"]
    messages.append({"role": "assistant", "content": reply})
    session['conversation_history'] = messages
    return reply

# Streaming request
def stream_openrouter(system_prompt, user_prompt):
    def event_stream():
        messages = session.get('conversation_history', [])
        if not messages:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})
        session['conversation_history'] = messages

        payload = {
            "model": "mistralai/mistral-7b-instruct:free",
            "messages": messages,
            "stream": True
        }
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }

        with requests.post(OR_URL, json=payload, headers=headers, stream=True) as r:
            for line in r.iter_lines():
                if line:
                    if line.startswith(b'data: '):
                        content = line[6:]
                        if content.strip() == b"[DONE]":
                            break
                        try:
                            json_chunk = content.decode('utf-8')
                            data = eval(json_chunk)  # minimal parsing; OpenRouter chunks follow GPT format
                            token = data["choices"][0]["delta"].get("content", "")
                            if token:
                                yield token
                        except Exception:
                            continue
    return event_stream()

# Routes
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/fetch_article", methods=["POST"])
def fetch_article():
    url = request.json.get("url")
    if not url or not is_valid_url(url):
        return jsonify({"error": "Valid URL is required"}), 400
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return jsonify({"error": "Could not fetch content"}), 400
        text = trafilatura.extract(downloaded)
        if not text:
            return jsonify({"error": "Extraction failed"}), 400
        return jsonify({"text": bleach.clean(text)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def is_valid_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme in ["http", "https"], result.netloc])
    except:
        return False

@app.route("/extract_claims", methods=["POST"])
def extract_claims():
    data = request.json
    text = data.get("text")
    focus = data.get("focus", "general")
    if not text:
        return jsonify({"error": "Text is required"}), 400
    session.pop('conversation_history', None)
    system_prompt = "You are a scientific assistant that extracts only explicit, testable scientific claims."
    user_prompt = f"Extract scientific claims from the following text in mode: {focus}.\nTEXT: {bleach.clean(text)}\nReply in numbered list."
    try:
        reply = call_openrouter(system_prompt, user_prompt)
        return jsonify({"claims": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/verify_claim", methods=["POST"])
def verify_claim():
    data = request.json
    claim = data.get("claim")
    sources = data.get("sources", [])
    if not claim:
        return jsonify({"error": "Claim is required"}), 400
    abstracts = "\n".join([f"{s['title']}: {s['abstract']}" for s in sources]) if sources else "No sources available."
    system_prompt = "You are a scientific assistant that verifies claims using logic and relevant abstracts."
    user_prompt = f"""Verify this claim using reasoning and any provided abstracts:

Claim: {bleach.clean(claim)}

Abstracts:
{abstracts}

Reply with True, False, or Inconclusive + brief justification."""
    return Response(stream_openrouter(system_prompt, user_prompt), content_type='text/plain')

@app.route("/generate_questions", methods=["POST"])
def generate_questions():
    data = request.json
    claim = data.get("claim")
    if not claim:
        return jsonify({"error": "Claim is required"}), 400
    system_prompt = "You are a scientific assistant suggesting follow-up research questions."
    user_prompt = f"Suggest 3 specific research questions related to this claim:\n{bleach.clean(claim)}"
    try:
        reply = call_openrouter(system_prompt, user_prompt)
        questions = [line.strip()[2:].strip() for line in reply.split("\n") if line.strip().startswith(("1.", "2.", "3."))]
        return jsonify({"questions": questions})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/generate_report", methods=["POST"])
def generate_report():
    data = request.json
    question = data.get("question")
    if not question:
        return jsonify({"error": "Question is required"}), 400
    system_prompt = "You are a scientific analyst generating detailed evidence-based reports."
    user_prompt = f"Generate a structured report answering this research question:\n{bleach.clean(question)}"
    return Response(stream_openrouter(system_prompt, user_prompt), content_type='text/plain')

@app.route("/search_articles", methods=["POST"])
def search_articles():
    query = request.json.get("query")
    if not query:
        return jsonify({"error": "Query is required"}), 400
    try:
        return jsonify({
            "crossref": fetch_crossref(query),
            "core": fetch_core(query)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def fetch_crossref(query):
    url = f"https://api.crossref.org/works?query={query}&rows=3"
    headers = {"User-Agent": "SciCheck/1.0 (mailto:info@example.com)"}
    r = requests.get(url, headers=headers)
    return [{
        "title": item.get("title", ["No title"])[0],
        "abstract": item.get("abstract", "Abstract not available"),
        "url": item.get("URL", "")
    } for item in r.json().get("message", {}).get("items", [])] if r.status_code == 200 else []

def fetch_core(query):
    url = f"https://core.ac.uk:443/api-v2/search/{query}?page=1&pageSize=3&metadata=true"
    headers = {"User-Agent": "SciCheck/1.0"}
    r = requests.get(url)
    return [{
        "title": item.get("title", "No title"),
        "abstract": item.get("description", "No abstract"),
        "url": item.get("downloadUrl", item.get("urls", {}).get("fullText", ""))
    } for item in r.json().get("data", [])] if r.status_code == 200 else []

if __name__ == "__main__":
    app.run(debug=True)
