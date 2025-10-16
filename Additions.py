# Database setup for session storage - PROPER IMPLEMENTATION
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

# FIXED: Enhanced verification prompts with better JSON structure
BASE_JSON_STRUCTURE = '''
Provide a JSON response with this exact structure:

{
    "verdict": "VERIFIED|PARTIALLY_SUPPORTED|INCONCLUSIVE|CONTRADICTED|SUPPORTED|NOT_SUPPORTED|FEASIBLE|POSSIBLE_BUT_UNPROVEN|UNLIKELY|NONSENSE",
    "justification": "Concise explanation under 1000 characters...",
    "sources": ["url1", "url2"] or [],
    "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"]
}

STRICT RULES:
- Verdict MUST match one of the specified options for this analysis mode
- Justification max 1000 characters  
- Sources: 1-2 relevant URLs or empty array
- Keywords: 3-5 relevant scientific/technical search terms
- Output ONLY valid JSON, no additional text
'''

verification_prompts = {
    "General Analysis of Testable Claims": f'''
Analyze this claim and provide a JSON response:
{BASE_JSON_STRUCTURE}

Claim: "{{claim}}"

JSON Response:
''',

    "Specific Focus on Scientific Claims": f'''
Analyze this scientific claim and provide a JSON response:
{BASE_JSON_STRUCTURE}

Claim: "{{claim}}"

JSON Response:
''',

    "Technology-Focused Extraction": f'''
Evaluate this technology claim and provide a JSON response:
{BASE_JSON_STRUCTURE}

Claim: "{{claim}}"

JSON Response:
'''
}

# FIXED: Completely rewrite the get_claim_details function
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
        
        # FIX: Safely get the analysis mode with validation
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
        
        # Generate verdict with proper error handling
        verdict_prompt = verification_prompts[current_analysis_mode].format(claim=claim_text)
        model_verdict_content = "Could not generate model verdict."
        questions = []
        search_keywords = []
        
        try:
            logging.info(f"Calling OpenRouter for model verdict for claim {claim_idx}...")
            res = call_openrouter(verdict_prompt)
            raw_llm_response = res.json()["choices"][0]["message"]["content"]
            logging.info(f"Raw LLM Response: {raw_llm_response}")
            
            # Parse JSON response safely
            try:
                # Clean the response - remove any markdown code blocks
                cleaned_response = re.sub(r'```json\s*|\s*```', '', raw_llm_response).strip()
                parsed_data = json.loads(cleaned_response)
                
                verdict = parsed_data.get('verdict', 'UNKNOWN')
                justification = parsed_data.get('justification', 'No justification provided.')
                sources = parsed_data.get('sources', [])
                search_keywords = parsed_data.get('keywords', [])
                
                # Format for display
                model_verdict_content = f"Verdict: **{verdict}**\n\nJustification: {justification}"
                if sources:
                    model_verdict_content += f"\n\nSources:\n" + "\n".join(f"- {src}" for src in sources)
                
                # Fallback for empty keywords
                if not search_keywords:
                    words = re.findall(r'\b[a-zA-Z]{5,}\b', claim_text)
                    search_keywords = words[:5] if words else [claim_text]
                    
            except json.JSONDecodeError as e:
                logging.warning(f"JSON parsing failed, using raw response: {e}")
                model_verdict_content = raw_llm_response
                words = re.findall(r'\b[a-zA-Z]{5,}\b', claim_text)
                search_keywords = words[:5] if words else [claim_text]
                
        except Exception as e:
            logging.error(f"Failed to process LLM response: {e}")
            model_verdict_content = f"Error generating verdict: {str(e)}"
            search_keywords = [claim_text]
        
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
