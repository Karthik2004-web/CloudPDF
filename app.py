import os
import time
import fitz  # PyMuPDF
from flask import Flask, request, render_template, send_file, redirect, url_for, session, jsonify
import google.generativeai as genai
import requests

# Configure Gemini API
GEMINI_API_KEY = "AIzaSyA_RMTkUPuHY3we3BnZ62H71qUwCazhVoY"  # Replace with your Gemini API key
genai.configure(api_key=GEMINI_API_KEY)

# The model name may have changed - use the correct one
model = genai.GenerativeModel('gemini-1.5-pro')  # Updated model name

app = Flask(__name__)
app.secret_key = 'secret-key-for-session'  # Needed to store summary in session

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Updated API credentials
USER_ID = "338ed70df2d643d885a8507e83f6a68d"
ULCA_API_KEY = "3221ec0400-0233-4a38-8e3b-ca93785b435d"

# Updated language dictionary with proper format
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
    # For very large documents, we might need to truncate
    # Gemini has a limit on input tokens
    max_length = 30000  # Adjust based on model limits
    truncated_text = text[:max_length] if len(text) > max_length else text

    prompt = f"Summarize the following text clearly and concisely, capturing all key points:\n\n{truncated_text}"
    try:
        # Add more error handling and debug info
        print(f"Attempting to generate content with model: gemini-1.5-pro")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error details: {str(e)}")
        # Attempt to list available models
        try:
            available_models = genai.list_models()
            models_info = "Available models:\n"
            for m in available_models:
                models_info += f"- {m.name}\n"
            return f"Summarization failed: {str(e)}\n\n{models_info}"
        except Exception as model_err:
            return f"Summarization failed: {str(e)}\nCouldn't list models: {str(model_err)}"


def process_pdf(document_path):
    doc = fitz.open(document_path)
    full_text = []
    for page_num, page in enumerate(doc):
        page_text = page.get_text()
        full_text.append(f"--- Page {page_num + 1} ---\n{page_text}\n")
    return "\n".join(full_text)


@app.route('/', methods=['GET', 'POST'])
def upload_file():
    summary = ""
    filename = ""
    error = ""

    if request.method == 'POST':
        if 'file' not in request.files:
            error = "No file part"
        else:
            file = request.files['file']
            if file.filename == '':
                error = "No selected file"
            elif not file.filename.endswith('.pdf'):
                error = "Please upload a PDF file"
            else:
                try:
                    timestamp = time.strftime("%Y%m%d-%H%M%S")
                    filepath = os.path.join(UPLOAD_FOLDER, f"uploaded_{timestamp}.pdf")
                    file.save(filepath)

                    extracted_text = process_pdf(filepath)
                    summary = summarize_text(extracted_text)

                    output_path = os.path.join(OUTPUT_FOLDER, f"summary_{timestamp}.txt")
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(summary)

                    session['summary'] = summary
                    filename = f"summary_{timestamp}.txt"
                    session['download_path'] = output_path

                except Exception as e:
                    error = f"Error processing PDF: {str(e)}"

    return render_template('index.html', summary=summary, filename=filename, error=error, languages=languages)


@app.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(OUTPUT_FOLDER, filename)
    return send_file(file_path, as_attachment=True)


@app.route('/translate', methods=['POST'])
def translate():
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Get content and language selections
    target_language_id = data.get('target_language')
    content = data.get('content')

    if not all([content, target_language_id]):
        return jsonify({"error": "Missing required fields"}), 400

    # Always use English (0) as source language
    source_lang_code = 0

    # Convert target language ID to int if it's sent as string
    try:
        target_lang_code = int(target_language_id)
    except ValueError:
        return jsonify({"error": "Invalid target language format"}), 400

    if target_lang_code not in languages:
        return jsonify({"error": "Invalid target language selection"}), 400

    try:
        # Convert integer codes to language codes
        source_language = languages[source_lang_code]["code"]
        target_language = languages[target_lang_code]["code"]

        # Step 1: Configure the translation pipeline
        config_payload = {
            "pipelineTasks": [
                {
                    "taskType": "translation",
                    "config": {
                        "language": {
                            "sourceLanguage": source_language,
                            "targetLanguage": target_language
                        }
                    }
                }
            ],
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

        # Step 2: Check configuration response and prepare translation request
        if config_response.status_code == 200:
            config_data = config_response.json()
            service_id = config_data["pipelineResponseConfig"][0]["config"][0]["serviceId"]
            callback_url = config_data["pipelineInferenceAPIEndPoint"]["callbackUrl"]
            inference_api_key_name = config_data["pipelineInferenceAPIEndPoint"]["inferenceApiKey"]["name"]
            inference_api_key_value = config_data["pipelineInferenceAPIEndPoint"]["inferenceApiKey"]["value"]

            # Step 3: Prepare and send the translation (compute) request
            compute_payload = {
                "pipelineTasks": [
                    {
                        "taskType": "translation",
                        "config": {
                            "language": {
                                "sourceLanguage": source_language,
                                "targetLanguage": target_language
                            },
                            "serviceId": service_id
                        }
                    }
                ],
                "inputData": {
                    "input": [
                        {
                            "source": content
                        }
                    ],
                    "audio": [
                        {
                            "audioContent": None
                        }
                    ]
                }
            }

            compute_headers = {
                "Content-Type": "application/json",
                inference_api_key_name: inference_api_key_value
            }

            compute_response = requests.post(callback_url, json=compute_payload, headers=compute_headers)

            # Step 4: Process the translation response
            if compute_response.status_code == 200:
                compute_data = compute_response.json()
                translated_text = compute_data["pipelineResponse"][0]["output"][0]["target"]
                return jsonify({
                    "status_code": 200,
                    "message": "Translation successful",
                    "translated_content": translated_text
                })
            else:
                return jsonify({
                    "status_code": compute_response.status_code,
                    "message": f"Translation failed: {compute_response.text}",
                    "translated_content": None
                })
        else:
            return jsonify({
                "status_code": config_response.status_code,
                "message": f"Pipeline configuration failed: {config_response.text}",
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
    app.run(debug=True)