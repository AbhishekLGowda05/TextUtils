from flask import Flask, render_template, request, url_for, send_from_directory, after_this_request
from datetime import datetime
import os
from modules.pdf_to_word import convert_pdf_to_word
from modules.ocr_to_word import ocr_pdf_to_word
from dotenv import load_dotenv

UPLOAD_FOLDER = "uploads"
CONVERTED_FOLDER = os.path.join("static", "converted")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONVERTED_FOLDER, exist_ok=True)


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # ~100 MB
app.secret_key = 'secret-key'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Load environment variables (e.g., Google credentials)
load_dotenv()



@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        pdf_file = request.files.get("pdf")
        title = request.form.get("title")
        author = request.form.get("author")
        pdf_type = request.form.get("pdf_type", "digital")
        use_google = request.form.get("use_google") == "on"

        if pdf_file:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            input_path = os.path.join(UPLOAD_FOLDER, f"{timestamp}_{pdf_file.filename}")
            pdf_file.save(input_path)

            output_filename = f"{timestamp}.docx"
            output_path = os.path.join(CONVERTED_FOLDER, output_filename)
            txt_filename = f"{timestamp}.txt"
            txt_path = os.path.join(CONVERTED_FOLDER, txt_filename)

            try:
                if pdf_type == "scanned":
                    ocr_pdf_to_word(
                        input_path,
                        output_path,
                        txt_path,
                        title=title,
                        author=author,
                        use_google=use_google,
                    )
                else:
                    convert_pdf_to_word(
                        input_path,
                        output_path,
                        txt_path,
                        title=title,
                        author=author,
                    )
            except ValueError as e:
                return render_template("index.html", error=str(e))
            finally:
                # remove uploaded file after processing
                if os.path.exists(input_path):
                    os.remove(input_path)

            download_docx = url_for("download", filename=output_filename)
            download_txt = url_for("download", filename=txt_filename)
            return render_template(
                "index.html",
                download_docx=download_docx,
                download_txt=download_txt,
            )

    return render_template("index.html")


@app.route("/download/<path:filename>")
def download(filename):
    file_path = os.path.join(CONVERTED_FOLDER, filename)

    @after_this_request
    def remove_file(response):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        finally:
            return response

    return send_from_directory(CONVERTED_FOLDER, filename, as_attachment=True)



if __name__ == '__main__':
    app.run(debug=True)
