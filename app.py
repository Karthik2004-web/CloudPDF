import os
import time


import fitz  # PyMuPDF
from flask import Flask, request, render_template, send_file, session, jsonify
from dotenv import load_dotenv
import google.generativeai as genai
import requests
import base64
from io import BytesIO

load_dotenv()  # Load environment variables from .env

# Load sensitive info from environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
USER_ID = os.getenv("ULCA_USER_ID")
ULCA_API_KEY = os.getenv("ULCA_API_KEY")
SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "default-secret-key")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

app = Flask(__name__)
app.secret_key = SECRET_KEY

UPLOAD_FOLDER = 'Uploads'
OUTPUT_FOLDER = 'output'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

languages = {
    0: {"code": "en", "name": "English"},
    1: {"code": "hi", "name": "Hindi"},
    2: {"code": "gom", "name": "Konkani"},
    3: {"code": "kn", "name": "Kannada"},
    4: {"code": "doi", "name": "Dogri"},
    5: {"code": "brx", "name": "Bodo"},
    6: {"code": "ur", "name": "Urdu"},
    7: {"code": "ta", "name": "Tamil"},
    8: {"code": "ks", "name": "Kashmiri"},
    9: {"code": "as", "name": "Assamese"},
    10: {"code": "bn", "name": "Bengali"},
    11: {"code": "mr", "name": "Marathi"},
    12: {"code": "sd", "name": "Sindhi"},
    13: {"code": "mai", "name": "Maithili"},
    14: {"code": "pa", "name": "Punjabi"},
    15: {"code": "ml", "name": "Malayalam"},
    16: {"code": "mni", "name": "Manipuri"},
    17: {"code": "te", "name": "Telugu"},
    18: {"code": "sa", "name": "Sanskrit"},
    19: {"code": "ne", "name": "Nepali"},
    20: {"code": "sat", "name": "Santali"},
    21: {"code": "gu", "name": "Gujarati"},
    22: {"code": "or", "name": "Odia"}
}

def summarize_text(text):
    max_length = 30000
    truncated_text = text[:max_length]
    prompt = f"Summarize the following text clearly and concisely, capturing all key points:\n\n{truncated_text}"
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Summarization failed: {str(e)}"

def answer_question(question, context):
    max_context_length = 30000
    truncated_context = context[:max_context_length]
    prompt = f"Based on the following context, answer the question concisely and accurately:\n\nContext:\n{truncated_context}\n\nQuestion: {question}"
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Failed to answer question: {str(e)}"

def extract_text_from_image(image_bytes):
    try:
        # Convert image bytes to base64 for Gemini API
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        # Prepare the content for Gemini API
        content = [
            {
                "mime_type": "image/jpeg",  # Adjust based on actual image type if needed
                "data": image_base64
            },
            "Extract all text from the provided image accurately."
        ]
        response = model.generate_content(content)
        return response.text.strip() if response.text else "No text detected in image"
    except Exception as e:
        return f"Image text extraction failed: {str(e)}"

def process_pdf(document_path):
    doc = fitz.open(document_path)
    extracted_text = []

    for i, page in enumerate(doc):
        page_text = page.get_text().strip()
        if page_text:
            # If text is present, use it directly
            extracted_text.append(f"--- Page {i+1} ---\n{page_text}")
        else:
            # If no text, try extracting images and processing with Gemini API
            images = page.get_images(full=True)
            for img_index, img in enumerate(images):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                try:
                    ocr_text = extract_text_from_image(image_bytes)
                    extracted_text.append(f"--- Page {i+1} (Image {img_index+1}) ---\n{ocr_text}")
                except Exception as e:
                    extracted_text.append(f"--- Page {i+1} (Image {img_index+1}) ---\nText extraction failed: {str(e)}")

    return "\n".join(extracted_text) if extracted_text else "No text or images found in the PDF."

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    summary = ""
    filename = ""
    error = ""
    extracted_text = session.get('extracted_text', "")

    if request.method == 'POST':
        file = request.files.get('file')
        if not file or file.filename == '':
            error = "No file selected"
        elif not file.filename.endswith('.pdf'):
            error = "Please upload a PDF file"
        else:
            try:
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                filepath = os.path.join(UPLOAD_FOLDER, f"uploaded_{timestamp}.pdf")
                file.save(filepath)

                extracted_text = process_pdf(filepath)
                if not extracted_text.strip():
                    error = "No readable text or images found in the PDF"
                else:
                    summary = summarize_text(extracted_text)

                    output_path = os.path.join(OUTPUT_FOLDER, f"summary_{timestamp}.txt")
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(summary)

                    session['summary'] = summary
                    session['extracted_text'] = extracted_text
                    session['download_path'] = output_path
                    filename = f"summary_{timestamp}.txt"
            except Exception as e:
                error = f"Error processing PDF: {str(e)}"

    return render_template('index.html', summary=summary, filename=filename, error=error, languages=languages)

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(os.path.join(OUTPUT_FOLDER, filename), as_attachment=True)

@app.route('/ask', methods=['POST'])
def ask_question():
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    question = data.get('question')
    if not question:
        return jsonify({"error": "No question provided"}), 400

    extracted_text = session.get('extracted_text', "")
    if not extracted_text:
        return jsonify({"error": "No PDF content available. Please upload a PDF first."}), 400

    try:
        answer = answer_question(question, extracted_text)
        return jsonify({"status_code": 200, "answer": answer})
    except Exception as e:
        return jsonify({"status_code": 500, "error": f"Failed to answer question: {str(e)}"})

@app.route('/translate', methods=['POST'])
def translate():
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    target_language_id = data.get('target_language')
    content = data.get('content')

    if not all([content, target_language_id]):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        target_lang_code = int(target_language_id)
        if target_lang_code not in languages:
            raise ValueError("Invalid language ID")
    except ValueError:
        return jsonify({"error": "Invalid target language format"}), 400

    source_language = languages[0]["code"]
    target_language = languages[target_lang_code]["code"]

    try:
        config_payload = {
            "pipelineTasks": [{
                "taskType": "translation",
                "config": {
                    "language": {
                        "sourceLanguage": source_language,
                        "targetLanguage": target_language
                    }
                }
            }],
            "pipelineRequestConfig": {
                "pipelineId": "64392f96daac500b55c543cd"
            }
        }

        config_headers = {
            "Content-Type": "application/json",
            "userID": os.getenv("ULCA_USER_ID"),
            "ulcaApiKey": os.getenv("ULCA_API_KEY")
        }

        config_response = requests.post(
            "https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline",
            json=config_payload,
            headers=config_headers
        )

        if config_response.status_code != 200:
            return jsonify({
                "status_code": config_response.status_code,
                "message": f"Pipeline configuration failed: {config_response.text}",
                "translated_content": None
            })

        config_data = config_response.json()
        endpoint = config_data["pipelineInferenceAPIEndPoint"]
        service_id = config_data["pipelineResponseConfig"][0]["config"][0]["serviceId"]

        compute_payload = {
            "pipelineTasks": [{
                "taskType": "translation",
                "config": {
                    "language": {
                        "sourceLanguage": source_language,
                        "targetLanguage": target_language
                    },
                    "serviceId": service_id
                }
            }],
            "inputData": {
                "input": [{"source": content}],
                "audio": [{"audioContent": None}]
            }
        }

        compute_headers = {
            "Content-Type": "application/json",
            endpoint["inferenceApiKey"]["name"]: endpoint["inferenceApiKey"]["value"]
        }

        compute_response = requests.post(endpoint["callbackUrl"], json=compute_payload, headers=compute_headers)

        if compute_response.status_code == 200:
            translated_text = compute_response.json()["pipelineResponse"][0]["output"][0]["target"]
            return jsonify({
                "status_code": 200,
                "message": "Translation successful",
                "translated_content": translated_text
            })

        return jsonify({
            "status_code": compute_response.status_code,
            "message": f"Translation failed: {compute_response.text}",
            "translated_content": None
        })
    except Exception as e:
        return jsonify({
            "status_code": 500,
            "message": f"Translation service error: {str(e)}",
            "translated_content": None
        })

@app.route('/languages', methods=['GET'])
def get_languages():
    return jsonify({str(id): lang["name"] for id, lang in languages.items()})

if __name__ == '__main__':
    app.run()