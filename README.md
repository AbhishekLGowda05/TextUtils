# Kannada PDF to Word Converter

This project is a simple Flask web application that converts Kannada PDF files to Word or text format. It also demonstrates how Google Cloud Vision can be used to perform OCR so that scanned PDF files or images can be converted to editable text.

## Features

- Upload a PDF file in Kannada and convert it to a Word document (`.docx`).
- Optional OCR support using Google Cloud Vision for scanned documents or images.
- Results can be downloaded as either a Word file or plain text (`.txt`).
- Select whether the uploaded PDF is **digital** or **scanned** before converting.
- Designed with minimal UI using an HTML form.

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd TextUtils
   ```
2. **Install dependencies**
   Make sure you have Python 3 installed. Install all requirements using pip:
   ```bash
   pip install -r requirements.txt
   ```
   If OCR support is desired, also install the Google Cloud client library:
   ```bash
   pip install google-cloud-vision
   ```

## Setting up Google Cloud Vision credentials

1. Create a project on Google Cloud Platform and enable the **Vision API**.
2. Create a Service Account, generate a key in JSON format and download it.
3. Set the environment variable `GOOGLE_APPLICATION_CREDENTIALS` to the path of that JSON file:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account.json
   ```
   The application will read this variable in order to authenticate requests to the Vision API.

## Running the application

Start the Flask development server with:
```bash
python app.py
```
Then open [http://localhost:5000](http://localhost:5000) in your browser. Use the form to upload a Kannada PDF file. After processing, a download link for the Word or text file will be provided.
Before converting, select whether the PDF is a **digital** or **scanned** document so the application knows which conversion method to use.

## Configuration notes

- **Fonts**: For correct rendering of Kannada text in the generated documents, install a Kannada font such as *Noto Sans Kannada* on your system. Some PDF conversion tools rely on the presence of appropriate fonts.
- **Upload size**: Flask's default upload size may be limited. You can change `MAX_CONTENT_LENGTH` in `app.py` if you need to accept larger files (for example, 20 MB):
  ```python
  app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024
  ```
- **Cleanup**: Temporary files created during conversion (such as intermediate images) should be removed after use to avoid filling the disk. Modify the conversion scripts in `modules/` to delete any files they create once conversion is completed.
- **Error handling**: If a corrupt or invalid PDF is uploaded, the application will report an error instead of crashing.

## Obtaining the `.txt` file

When you upload a PDF and choose OCR processing, the recognized text is saved to a `.txt` file. After the conversion completes, the application will provide a link to download this text file. You can then open it with any text editor for further editing or search.

