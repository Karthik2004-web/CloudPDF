import os
import time
from flask import Flask, request, render_template, send_file, session, jsonify, redirect, url_for
from dotenv import load_dotenv
import google.generativeai as genai
import requests

# Load environment variables from .env
load_dotenv()

# Load sensitive info from environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
USER_ID = os.getenv("ULCA_USER_ID")
ULCA_API_KEY = os.getenv("ULCA_API_KEY")
SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "default-secret-key")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Define folders
UPLOAD_FOLDER = 'Uploads'
OUTPUT_FOLDER = 'output'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Language options for translation
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

# Root route - redirect to homepage
@app.route('/')
def root():
    return redirect(url_for('home'))

@app.route('/home')
def home():
    return render_template('homepage.html')

# Keep the original route for backward compatibility with existing forms
@app.route('/', methods=['POST'])
def root_post():
    return upload_file()

@app.route('/index', methods=['GET', 'POST'])
def upload_file():
    summary = ""
    filename = ""
    error = ""

    if request.method == 'POST':
        file = request.files.get('file')
        if not file or file.filename == '':
            error = "No file selected"
        elif not file.filename.endswith('.pdf'):
            error = "Please upload a PDF file"
        else:
            try:
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                file_path = os.path.join(UPLOAD_FOLDER, f"uploaded_{timestamp}.pdf")
                file.save(file_path)

                # Check file size
                file_size = os.path.getsize(file_path) / (1024 * 1024)
                if file_size > 50:
                    raise Exception("File size exceeds 50MB limit for File API")

                # Upload PDF to Gemini
                uploaded_file = genai.upload_file(path=file_path, mime_type='application/pdf')
                session['file_name'] = uploaded_file.name

                # Summarize using Gemini
                prompt = """Summarize this document clearly and concisely, capturing all key points. 
                Please ensure the summary is informative and easy to understand.
                use *** for bold points and * for italics and use \lnn in the response for new line. 
                please use \lnn for new line , do not use any other special characters.
                please please please use \lnn for everynew line, new line helps to make the summary more readable.
                """
                response = model.generate_content(
                    contents=[uploaded_file, prompt]
                )
                summary = response.text
                print(summary)
                # Save to file
                output_path = os.path.join(OUTPUT_FOLDER, f"summary_{timestamp}.txt")
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(summary)

                session['summary'] = summary
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

    file_name = session.get('file_name')
    if not file_name:
        return jsonify({"error": "No PDF uploaded"}), 400

    try:
        file_reference = genai.get_file(file_name)
        prompt = f"Based on the document, answer the following question concisely and accurately: {question}"
        response = model.generate_content(contents=[file_reference, prompt])
        return jsonify({"status_code": 200, "answer": response.text})
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
            "userID": USER_ID,
            "ulcaApiKey": ULCA_API_KEY
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
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
