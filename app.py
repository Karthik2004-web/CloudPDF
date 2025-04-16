# # flask_pdf_summarizer.py
#
# import os
# import io
# import time
# import fitz  # PyMuPDF
# import cv2
# import numpy as np
# import pytesseract
# from PIL import Image
# import warnings
# from flask import Flask, request, render_template, send_file
# import google.generativeai as genai
#
# # Configure Tesseract path
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
#
# # Configure Gemini API
# GEMINI_API_KEY = "AIzaSyA_RMTkUPuHY3we3BnZ62H71qUwCazhVoY"  # Replace with your Gemini API key
# genai.configure(api_key=GEMINI_API_KEY)
# model = genai.GenerativeModel('gemini-pro')
#
# app = Flask(__name__)
#
# UPLOAD_FOLDER = 'uploads'
# OUTPUT_FOLDER = 'output'
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# os.makedirs(OUTPUT_FOLDER, exist_ok=True)
#
# def preprocess_image(image):
#     img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
#     gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
#     denoised = cv2.fastNlMeansDenoising(gray, h=30)
#     _, threshold = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
#     scaled = cv2.resize(threshold, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
#     return Image.fromarray(scaled)
#
# def extract_text_from_image(img):
#     try:
#         processed_img = preprocess_image(img)
#         text = pytesseract.image_to_string(processed_img, config='--psm 6 --oem 3 -c preserve_interword_spaces=1')
#         return text.strip()
#     except Exception as e:
#         warnings.warn(f"Image processing failed: {str(e)}")
#         return ""
#
# def summarize_text(text):
#     prompt = f"Summarize the following text:\n\n{text}"
#     try:
#         response = model.generate_content(prompt)
#         return response.text
#     except Exception as e:
#         return f"Summarization failed: {str(e)}"
#
# def process_pdf(document_path):
#     doc = fitz.open(document_path)
#     full_text = []
#     for page_num, page in enumerate(doc):
#         page_text = page.get_text()
#         if len(page_text.strip()) < 50:
#             img_list = page.get_images(full=True)
#             for img in img_list:
#                 xref = img[0]
#                 base_image = doc.extract_image(xref)
#                 image = Image.open(io.BytesIO(base_image["image"]))
#                 page_text += "\n" + extract_text_from_image(image)
#         full_text.append(f"--- Page {page_num+1} ---\n{page_text}\n")
#     return "\n".join(full_text)
#
# @app.route('/', methods=['GET', 'POST'])
# def upload_file():
#     if request.method == 'POST':
#         if 'file' not in request.files:
#             return "No file part"
#         file = request.files['file']
#         if file.filename == '':
#             return "No selected file"
#         if file:
#             timestamp = time.strftime("%Y%m%d-%H%M%S")
#             filepath = os.path.join(UPLOAD_FOLDER, f"uploaded_{timestamp}.pdf")
#             file.save(filepath)
#
#             extracted_text = process_pdf(filepath)
#             summary = summarize_text(extracted_text)
#
#             output_path = os.path.join(OUTPUT_FOLDER, f"summary_{timestamp}.txt")
#             with open(output_path, 'w', encoding='utf-8') as f:
#                 f.write(summary)
#
#             return send_file(output_path, as_attachment=True)
#
#     return render_template('index.html')
#
# if __name__ == '__main__':
#     app.run(debug=True)
# flask_pdf_summarizer.py

# flask_pdf_summarizer.py

import os
import time
import fitz  # PyMuPDF
from flask import Flask, request, render_template, send_file, redirect, url_for, session
import google.generativeai as genai

# Configure Gemini API
GEMINI_API_KEY = "AIzaSyA_RMTkUPuHY3we3BnZ62H71qUwCazhVoY"  # Replace with your Gemini API key
genai.configure(api_key=GEMINI_API_KEY)

# The model name may have changed - use the correct one
# According to the error, we need to check the available models
model = genai.GenerativeModel('gemini-1.5-pro')  # Updated model name

app = Flask(__name__)
app.secret_key = 'secret-key-for-session'  # Needed to store summary in session

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


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

    return render_template('index.html', summary=summary, filename=filename, error=error)


@app.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(OUTPUT_FOLDER, filename)
    return send_file(file_path, as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True)