import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, send_file, abort, flash
from werkzeug.utils import secure_filename
from modules import pdf_to_word, ocr_to_word

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # ~100 MB
app.secret_key = 'secret-key'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload():
    pdf_file = request.files.get('pdf')
    if not pdf_file:
        flash('No file uploaded')
        return redirect(url_for('index'))

    title = request.form.get('title')
    author = request.form.get('author')
    pdf_type = request.form.get('pdf_type', 'digital')

    filename = secure_filename(pdf_file.filename)
    if not filename.lower().endswith('.pdf'):
        flash('Only PDF files are allowed')
        return redirect(url_for('index'))

    unique_id = uuid.uuid4().hex
    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_id + '_' + filename)
    pdf_file.save(upload_path)

    docx_filename = unique_id + '.docx'
    txt_filename = unique_id + '.txt'
    docx_path = os.path.join(app.config['UPLOAD_FOLDER'], docx_filename)
    txt_path = os.path.join(app.config['UPLOAD_FOLDER'], txt_filename)

    try:
        if pdf_type == 'scanned':
            ocr_to_word.convert(upload_path, docx_path, txt_path, title=title, author=author)
        else:
            pdf_to_word.convert(upload_path, docx_path, txt_path, title=title, author=author)
    except Exception as e:
        flash(f'Conversion failed: {e}')
        os.remove(upload_path)
        return redirect(url_for('index'))

    os.remove(upload_path)

    return render_template('result.html', docx_filename=docx_filename, txt_filename=txt_filename)


@app.route('/download/<path:filename>')
def download_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(file_path):
        abort(404)
    try:
        return_data = send_file(file_path, as_attachment=True)
    finally:
        try:
            os.remove(file_path)
        except OSError:
            pass
    return return_data

if __name__ == '__main__':
    app.run(debug=True)
