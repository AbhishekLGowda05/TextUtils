import os
from flask import Flask, request, render_template, send_from_directory

from modules.pdf_to_word import convert_pdf

app = Flask(__name__)
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        pdf_file = request.files.get("pdf")
        if not pdf_file or not pdf_file.filename:
            return "No PDF uploaded", 400
        pdf_path = os.path.join(app.config["UPLOAD_FOLDER"], pdf_file.filename)
        pdf_file.save(pdf_path)
        docx_path, _ = convert_pdf(pdf_path, app.config["UPLOAD_FOLDER"])
        return send_from_directory(
            app.config["UPLOAD_FOLDER"], os.path.basename(docx_path), as_attachment=True
        )
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
