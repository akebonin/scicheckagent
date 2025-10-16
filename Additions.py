# Add to imports section
import base64
from PIL import Image
import pytesseract

# Add after the existing helper functions

def analyze_image_with_ocr(image_path):
    """Extract text from image using OCR"""
    try:
        # Use Tesseract OCR to extract text from image
        extracted_text = pytesseract.image_to_string(Image.open(image_path))
        return extracted_text.strip()
    except Exception as e:
        logging.error(f"OCR processing failed: {e}")
        return ""

def transcribe_video(video_path):
    """Transcribe video using TurboScribe API or similar service"""
    # This is a placeholder - you'll need to implement actual video transcription
    # For now, we'll return a message about the feature
    logging.info(f"Video transcription called for: {video_path}")
    return "Video transcription feature requires TurboScribe API integration. Please paste the text manually for now."

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

# Add new API endpoints after existing endpoints

@app.route("/api/process-image", methods=["POST"])
def process_image():
    """Process uploaded image and extract text using OCR"""
    try:
        if 'image' not in request.files:
            return jsonify({"error": "No image file provided"}), 400
        
        image_file = request.files['image']
        if image_file.filename == '':
            return jsonify({"error": "No image file selected"}), 400
        
        # Save the uploaded image
        image_path = save_uploaded_file(image_file)
        if not image_path:
            return jsonify({"error": "Failed to save image"}), 500
        
        # Extract text using OCR
        extracted_text = analyze_image_with_ocr(image_path)
        
        # Clean up the uploaded file
        try:
            os.remove(image_path)
        except:
            pass
        
        if not extracted_text:
            return jsonify({"error": "Could not extract text from image. Please ensure the image contains clear text."}), 400
        
        return jsonify({"extracted_text": extracted_text})
        
    except Exception as e:
        logging.error(f"Error in process_image endpoint: {e}")
        return jsonify({"error": f"Failed to process image: {str(e)}"}), 500

@app.route("/api/process-video", methods=["POST"])
def process_video():
    """Process uploaded video and extract transcription"""
    try:
        if 'video' not in request.files:
            return jsonify({"error": "No video file provided"}), 400
        
        video_file = request.files['video']
        if video_file.filename == '':
            return jsonify({"error": "No video file selected"}), 400
        
        # Save the uploaded video
        video_path = save_uploaded_file(video_file)
        if not video_path:
            return jsonify({"error": "Failed to save video"}), 500
        
        # Transcribe video (placeholder implementation)
        transcription = transcribe_video(video_path)
        
        # Clean up the uploaded file
        try:
            os.remove(video_path)
        except:
            pass
        
        return jsonify({"transcription": transcription, "note": "Video transcription requires TurboScribe API integration. Please paste the text manually for now."})
        
    except Exception as e:
        logging.error(f"Error in process_video endpoint: {e}")
        return jsonify({"error": f"Failed to process video: {str(e)}"}), 500

@app.route("/api/transcribe-video-url", methods=["POST"])
def transcribe_video_url():
    """Transcribe video from URL using TurboScribe API"""
    try:
        data = request.json
        video_url = data.get("video_url")
        
        if not video_url:
            return jsonify({"error": "No video URL provided"}), 400
        
        # Placeholder for TurboScribe API integration
        # You would need to implement actual API call to TurboScribe
        logging.info(f"Video URL transcription requested for: {video_url}")
        
        return jsonify({
            "transcription": "Video URL transcription requires TurboScribe API integration. Please paste the text manually for now.",
            "note": "This feature requires TurboScribe API key and proper integration."
        })
        
    except Exception as e:
        logging.error(f"Error in transcribe_video_url endpoint: {e}")
        return jsonify({"error": f"Failed to transcribe video URL: {str(e)}"}), 500
