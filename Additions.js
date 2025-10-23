@app.route("/api/analyze", methods=["POST"])
def analyze():
    # ... existing code ...
    
    claims_list = [c for c in claims_list if len(c) > 10 and not c.lower().startswith(("output:", "text:", "no explicit claims found"))]

    # RE-RETRIEVE and UPDATE the session data
    article_cache_data = get_analysis(article_id)
    if article_cache_data:
        article_cache_data["claims_data"] = [{"text": claim_text} for claim_text in claims_list]
        store_analysis(article_id, article_cache_data)  # ← Store with claims data
    
    return jsonify({"claims": claims_list})


// In your autoLoadClaimDetails function, modify to use cached data when available
async function autoLoadClaimDetails(claims) {
    const promises = claims.map(async (claim, index) => {
        const claimId = `claim-${index}`;
        const verdictContainerId = `model-verdict-${claimId}`;
        const questionsContainerId = `questions-list-${claimId}`;
        const externalVerdictContainerId = `external-verdict-${claimId}`;
        const externalSourcesContainerId = `external-sources-${claimId}`;

        try {
            // Check if we already have model details
            const claimElement = document.getElementById(claimId);
            if (claimElement && claimElement.dataset.hasModelDetails) {
                // Details already loaded, skip API call
                console.log(`Using cached model details for claim ${index}`);
            } else {
                await getModelDetails(index, verdictContainerId, questionsContainerId, null, true);
            }

            if (usePapersToggle.checked) {
                // Check if we already have external verification
                if (claimElement && claimElement.dataset.hasExternalDetails) {
                    console.log(`Using cached external verification for claim ${index}`);
                } else {
                    await verifyExternal(index, externalVerdictContainerId, externalSourcesContainerId, null, true);
                }
            }
        } catch (error) {
            console.error(`Error loading details for claim ${index}:`, error);
        }
    });

    for (let i = 0; i < claims.length; i++) {
        toggleLoading(runAnalysisBtn, true, 'Analyzing', `Claim ${i + 1} of ${claims.length}`);
        await promises[i];
    }
    toggleLoading(runAnalysisBtn, false);
}

// Add cached indicators to the UI
function addCachedIndicator(element, type) {
    const indicator = document.createElement('span');
    indicator.className = 'badge bg-secondary ms-2';
    indicator.textContent = 'Cached';
    indicator.title = `This ${type} was loaded from cache`;
    element.appendChild(indicator);
}

// Modify the displayClaimsStructure function to mark elements with cache status
function displayClaimsStructure(claims) {
    claims.forEach((claimText, index) => {
        const claimId = `claim-${index}`;
        const claimHtml = `
        <div class="claim-card" id="${claimId}">
            <h5>Claim ${index + 1}</h5>
            <p class="claim-text mb-3">${escapeHTML(claimText)}</p>
            <strong>Model Verdict:</strong>
            <div id="model-verdict-${claimId}" class="verdict-box model-verdict-box mb-3" style="min-height: 50px;">
                <span class="text-muted">Loading model verdict...</span>
            </div>
            <strong>Suggested Research Questions:</strong>
            <ul id="questions-list-${claimId}" class="question-list list-group list-group-flush mb-3">
                <li class="list-group-item">
                    <span class="text-muted">Loading questions...</span>
                </li>
            </ul>
            <hr>
            <strong>External Verification (Semantic Scholar, Crossref, CORE & PubMed):</strong>
            <div id="external-verdict-${claimId}" class="verdict-box mb-2" style="min-height: 50px;">
                ${usePapersToggle.checked ? '<span class="text-muted">Loading external verification...</span>' : 'External verification is toggled off.'}
            </div>
            <ul id="external-sources-${claimId}" class="source-list list-unstyled ps-3 mb-3"></ul>
        </div>
        `;
        resultsContainer.innerHTML += claimHtml;
    });

    autoLoadClaimDetails(claims);
}






// Add this helper function
function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = () => resolve(reader.result);
        reader.onerror = error => reject(error);
    });
}

// Replace the processVideo function
async function processVideo() {
    if (!currentVideoFile) {
        alert('Please select a video first');
        return;
    }
    
    toggleLoading(processVideoBtn, true, 'Processing video...');
    
    try {
        // Convert video to audio first using the browser
        const audioBlob = await extractAudioFromVideo(currentVideoFile);
        const base64Audio = await fileToBase64(audioBlob);
        
        // Use your Vercel proxy URL - replace with your actual Vercel URL
        const vercelProxyUrl = 'https://your-app.vercel.app/api/transcribe';
        
        const response = await fetch(vercelProxyUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ audioData: base64Audio })
        });
        
        const data = await response.json();
        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Failed to transcribe video');
        }
        
        textInput.value = data.transcription;
        inputMethodSelect.value = 'paste';
        inputMethodSelect.dispatchEvent(new Event('change'));
        alert('Video transcribed successfully! Ready for analysis.');
    } catch (error) {
        console.error('Video processing error:', error);
        alert(`Error processing video: ${error.message}`);
    } finally {
        toggleLoading(processVideoBtn, false);
    }
}

// Replace the transcribeVideoUrl function
async function transcribeVideoUrl() {
    const videoUrl = videoUrlInput.value.trim();
    if (!videoUrl) {
        alert('Please enter a video URL');
        return;
    }
    
    if (!videoUrl.match(/^https?:\/\/[^\s/$.?#].[^\s]*$/)) {
        alert('Invalid URL format. Please use a valid URL starting with http:// or https://.');
        return;
    }
    
    toggleLoading(transcribeVideoUrlBtn, true, 'Transcribing...');
    
    try {
        // Use your Vercel proxy URL - replace with your actual Vercel URL
        const vercelProxyUrl = 'https://your-app.vercel.app/api/transcribe';
        
        const response = await fetch(vercelProxyUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ audioUrl: videoUrl })
        });
        
        const data = await response.json();
        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Failed to transcribe video URL');
        }
        
        textInput.value = data.transcription;
        inputMethodSelect.value = 'paste';
        inputMethodSelect.dispatchEvent(new Event('change'));
        alert('Video URL transcribed successfully!');
    } catch (error) {
        console.error('Video URL transcription error:', error);
        alert(`Error transcribing video URL: ${error.message}`);
    } finally {
        toggleLoading(transcribeVideoUrlBtn, false);
    }
}

// Helper to extract audio from video in the browser
function extractAudioFromVideo(videoFile) {
    return new Promise((resolve, reject) => {
        const video = document.createElement('video');
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        
        video.src = URL.createObjectURL(videoFile);
        video.crossOrigin = 'anonymous';
        
        video.onloadedmetadata = () => {
            const source = audioContext.createMediaElementSource(video);
            const destination = audioContext.createMediaStreamDestination();
            
            source.connect(destination);
            
            video.play().then(() => {
                // For now, we'll send the video file directly to the proxy
                // The proxy will handle audio extraction
                URL.revokeObjectURL(video.src);
                resolve(videoFile);
            }).catch(reject);
        };
        
        video.onerror = reject;
    });
}






def transcribe_video(video_path):
    """Transcribe uploaded video using free whisper-api.com"""
    try:
        # Extract audio from video
        audio_path = video_path + ".mp3"
        video_clip = VideoFileClip(video_path)
        video_clip.audio.write_audiofile(audio_path)
        video_clip.close()

        # Use free whisper-api.com instead of OpenAI
        with open(audio_path, "rb") as audio_file:
            files = {"file": audio_file}
            response = requests.post(
                "https://whisper-api.com/api/v1/transcribe",
                files=files,
                timeout=60
            )
        
        if response.status_code == 200:
            result = response.json()
            transcription = result.get("text", "")
        else:
            raise ValueError(f"Whisper API error: {response.status_code} - {response.text}")

        # Clean up audio file
        os.remove(audio_path)
        logging.info(f"Video transcribed successfully using free API: {video_path}")
        return transcription
        
    except Exception as e:
        logging.error(f"Free API transcription failed: {e}")
        if os.path.exists(audio_path):
            os.remove(audio_path)
        raise ValueError(f"Failed to transcribe video: {str(e)}")




import unicodedata  # Added for Unicode normalization

# ... (other imports remain unchanged)

# Helper function to normalize text
def normalize_text(text):
    """Normalize Unicode characters to ASCII and replace specific characters."""
    if not text:
        return text
    # Normalize to decomposed form and encode to ASCII, ignoring non-ASCII characters
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')
    # Replace specific characters
    text = text.replace('β', 'beta').replace('–', '-').replace('—', '-').replace('’', "'")
    return text

# ... (other helper functions unchanged)

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
            # Normalize cached report content
            normalized_report = normalize_text(claim_data_in_cache[report_key])
            yield f"data: {json.dumps({'content': normalized_report})}\n\n"
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
                                    # Normalize content for streaming
                                    normalized_content = normalize_text(content)
                                    full_report_content += content  # Store original for cache
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
                # Store original content in cache, normalization happens on retrieval
                claim_data_in_cache[report_key] = full_report_content
                # Update the session data
                store_analysis(current_article_id, article_cache_data)
                update_access_time(current_article_id)
            yield f"data: [DONE]\n\n"

    return Response(stream_response(), mimetype='text/event-stream')

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
    for claim_idx, claim_item_in_cache in enumerate(claims_data_in_cache):
        if "model_verdict" not in claim_item_in_cache or "questions" not in claim_item_in_cache:
            logging.warning(f"Skipping claim {claim_idx} for PDF: missing model verdict or questions in cache.")
            continue

        for q_idx, question in enumerate(claim_item_in_cache.get('questions', [])):
            report_key = f"q{q_idx}_report"
            if report_key in claim_item_in_cache and claim_item_in_cache[report_key]:
                # Check if this report is selected
                report_id = f"claim-{claim_idx}-question-{q_idx}"
                if not selected_reports or report_id in selected_reports:
                    pdf_reports.append({
                        "claim_text": claim_item_in_cache['text'],
                        "model_verdict": normalize_text(claim_item_in_cache['model_verdict']),
                        "external_verdict": normalize_text(claim_item_in_cache.get('external_verdict', 'Not verified externally.')),
                        "sources": claim_item_in_cache.get('sources', []),
                        "question": normalize_text(question),
                        "report": normalize_text(claim_item_in_cache[report_key])
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
                    link_text = f'<link href="{escaped_url}">{link_text}</link>'
                y = draw_paragraph(p, f"- {link_text}", styles['SourceLink'], y, width)

        y = draw_paragraph(p, f"<b>Research Question:</b> {item['question']}", styles['SectionHeading'], y, width)

        if item.get('report'):
            y = draw_paragraph(p, "<b>AI Research Report:</b>", styles['SectionHeading'], y, width)
            report_content_formatted = item['report']
            report_content_formatted = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', report_content_formatted)
            report_content_formatted = re.sub(r'\[(.*?)\]\((https?://[^\s\]]+)\)', r'<link href="\2">\1</link>', report_content_formatted)
            y = draw_paragraph(p, report_content_formatted, styles['ReportBody'], y, width)
        y -= 20

    p.save()
    buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name="SciCheck_AI_Report.pdf")

def draw_paragraph(pdf_canvas, text_content, style, y_pos, page_width, left_margin=0.75*inch, right_margin=0.75*inch):
    available_width = page_width - left_margin - right_margin
    # Normalize text for PDF rendering
    text_content = normalize_text(text_content)
    # Replace markdown newlines with HTML <br/> for ReportLab Paragraph
    text_content = text_content.replace('\n', '<br/>')
    para = Paragraph(text_content, style)
    w, h = para.wrapOn(pdf_canvas, available_width, 0)
    if y_pos - h < 0.75*inch:
        pdf_canvas.showPage()
        y_pos = A4[1] - 0.75*inch
    para.drawOn(pdf_canvas, left_margin, y_pos - h)
    return y_pos - h - style.spaceAfter

# ... (rest of the backend code unchanged)
