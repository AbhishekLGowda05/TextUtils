from flask import Flask, render_template, request, url_for, send_from_directory, after_this_request, flash
from datetime import datetime
import os
import logging
from modules.pdf_to_word import convert_pdf_to_word
from modules.ocr_to_word import ocr_pdf_to_word
from modules.legacy_kannada import detect_legacy_encoding, is_kannada_text
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

UPLOAD_FOLDER = "uploads"
CONVERTED_FOLDER = os.path.join("static", "converted")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONVERTED_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # ~100 MB
app.secret_key = 'secret-key-change-in-production'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Load environment variables (e.g., Google credentials)
load_dotenv()

def validate_pdf_file(file):
    """Validate uploaded PDF file."""
    if not file:
        return False, "No file selected"
    
    if file.filename == '':
        return False, "No file selected"
    
    if not file.filename.lower().endswith('.pdf'):
        return False, "File must be a PDF"
    
    return True, "Valid"

def cleanup_temp_files(*file_paths):
    """Clean up temporary files safely."""
    for file_path in file_paths:
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to clean up {file_path}: {e}")

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        pdf_file = request.files.get("pdf")
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        pdf_type = request.form.get("pdf_type", "digital")
        use_google = request.form.get("use_google") == "on"
        debug_mode = request.form.get("debug_mode") == "on"  # Add debug mode

        # Validate file
        is_valid, error_msg = validate_pdf_file(pdf_file)
        if not is_valid:
            logger.warning(f"File validation failed: {error_msg}")
            return render_template("index.html", error=error_msg)

        # Create unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        safe_filename = "".join(c for c in pdf_file.filename if c.isalnum() or c in '._-')
        input_path = os.path.join(UPLOAD_FOLDER, f"{timestamp}_{safe_filename}")
        
        output_filename = f"{timestamp}.docx"
        output_path = os.path.join(CONVERTED_FOLDER, output_filename)
        txt_filename = f"{timestamp}.txt"
        txt_path = os.path.join(CONVERTED_FOLDER, txt_filename)

        try:
            # Save uploaded file
            pdf_file.save(input_path)
            logger.info(f"File uploaded: {input_path}")

            # Log processing parameters
            logger.info(f"Processing PDF: type={pdf_type}, use_google={use_google}, "
                       f"debug_mode={debug_mode}, title='{title}', author='{author}'")

            if pdf_type == "scanned":
                # Process scanned PDF with OCR
                logger.info("Processing scanned PDF with OCR")
                
                # Set vision page limit to control costs (increased for better coverage)
                vision_page_limit = 20 if use_google else None
                
                docx_path, txt_path_result = ocr_pdf_to_word(
                    input_path,
                    output_path,
                    txt_path,
                    title=title or None,
                    author=author or None,
                    use_google=use_google,
                    vision_page_limit=vision_page_limit,
                    ocr_timeout=60,  # Increased timeout for better processing
                    debug_mode=debug_mode,  # Pass debug mode
                )
                
                # Validate OCR results
                try:
                    with open(txt_path_result, 'r', encoding='utf-8') as f:
                        extracted_text = f.read()
                    
                    if not extracted_text.strip():
                        flash("Warning: No text was extracted from the PDF. The file might be image-only or contain non-standard fonts.", "warning")
                    elif not is_kannada_text(extracted_text):
                        flash("Warning: No Kannada text detected. Please verify the PDF contains Kannada content or try OCR mode.", "warning")
                    else:
                        flash("PDF successfully converted with OCR!", "success")
                        
                except Exception as e:
                    logger.warning(f"Could not validate OCR results: {e}")
                
            else:
                # Process digital PDF
                logger.info("Processing digital PDF")
                
                docx_path, txt_path_result = convert_pdf_to_word(
                    input_path,
                    output_path,
                    txt_path,
                    title=title or None,
                    author=author or None,
                )
                
                # Validate digital PDF results
                try:
                    with open(txt_path_result, 'r', encoding='utf-8') as f:
                        extracted_text = f.read()
                    
                    if not extracted_text.strip():
                        flash("Warning: No text was extracted. The PDF might be scanned or image-based. Try 'Scanned PDF' mode.", "warning")
                    elif detect_legacy_encoding(extracted_text):
                        flash("Warning: Legacy Kannada fonts detected. Text may not display correctly. Consider using OCR mode for better results.", "warning")
                    elif not is_kannada_text(extracted_text):
                        flash("Warning: No Kannada text detected. Please verify the PDF contains Kannada content.", "warning")
                    else:
                        flash("PDF successfully converted!", "success")
                        
                except Exception as e:
                    logger.warning(f"Could not validate digital PDF results: {e}")

            logger.info(f"Conversion successful: {docx_path}, {txt_path_result}")

        except ValueError as e:
            error_msg = str(e)
            logger.error(f"Validation error: {error_msg}")
            cleanup_temp_files(input_path, output_path, txt_path)
            return render_template("index.html", error=error_msg)
            
        except FileNotFoundError as e:
            error_msg = "Required system components not found. Please check Tesseract installation."
            logger.error(f"File not found error: {e}")
            cleanup_temp_files(input_path, output_path, txt_path)
            return render_template("index.html", error=error_msg)
            
        except PermissionError as e:
            error_msg = "Permission denied. Please check file permissions."
            logger.error(f"Permission error: {e}")
            cleanup_temp_files(input_path, output_path, txt_path)
            return render_template("index.html", error=error_msg)
            
        except Exception as e:
            error_msg = f"An unexpected error occurred: {str(e)}"
            logger.error(f"Unexpected error: {e}", exc_info=True)
            cleanup_temp_files(input_path, output_path, txt_path)
            return render_template("index.html", error=error_msg)
            
        finally:
            # Always clean up uploaded file
            cleanup_temp_files(input_path)

        # Generate download URLs
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
    """Serve file for download and clean up afterwards."""
    file_path = os.path.join(CONVERTED_FOLDER, filename)
    
    # Validate file exists and is safe
    if not os.path.exists(file_path):
        logger.warning(f"Download requested for non-existent file: {filename}")
        return "File not found", 404
    
    # Check if filename is safe (no directory traversal)
    if '..' in filename or filename.startswith('/'):
        logger.warning(f"Unsafe download request: {filename}")
        return "Invalid filename", 400

    @after_this_request
    def remove_file(response):
        """Clean up file after download."""
        cleanup_temp_files(file_path)
        return response

    logger.info(f"Serving file for download: {filename}")
    return send_from_directory(CONVERTED_FOLDER, filename, as_attachment=True)

@app.errorhandler(413)
def too_large(e):
    """Handle file too large error."""
    logger.warning("File upload too large")
    return render_template("index.html", error="File too large. Maximum size is 100MB."), 413

@app.errorhandler(500)
def internal_error(e):
    """Handle internal server errors."""
    logger.error(f"Internal server error: {e}")
    return render_template("index.html", error="Internal server error. Please try again."), 500

if __name__ == '__main__':
    logger.info("Starting TextUtils Flask application")
    app.run(debug=True)
