import os
import fitz  # PyMuPDF
from flask import (
    Flask,
    request,
    render_template,
    send_from_directory,
    url_for,
    session,
    redirect,
)
from werkzeug.utils import secure_filename
from model import initialize_summarizer, generate_summary, format

app = Flask(__name__)
# Generate a secret key for sessions (use a fixed one in production)
app.secret_key = os.urandom(24)  # Random key for development


# Set the upload folder
UPLOAD_FOLDER = "uploads/"
EXTRACTED_FOLDER = "extracted_text/"
PREVIEW_FOLDER = "previews"  # Store previews in a static folder for easy access
ALLOWED_EXTENSIONS = {"pdf"}
tokenizer, model = initialize_summarizer()


# Ensure the folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(EXTRACTED_FOLDER, exist_ok=True)
os.makedirs(PREVIEW_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["EXTRACTED_FOLDER"] = EXTRACTED_FOLDER
app.config["PREVIEW_FOLDER"] = PREVIEW_FOLDER

# List to keep track of uploads
uploads = []


def format_for_html(text: str) -> str:
    """
    Formats text for proper display in HTML by:
    1. Preserving paragraph spacing
    2. Converting newlines to HTML tags
    """
    # First apply your existing formatting
    formatted_text = format(text)

    # Convert to HTML-friendly format
    html_text = formatted_text.replace("\n\n", "</p><p>").replace("\n", "<br>")
    return f"<p>{html_text}</p>"


@app.route("/toggle_dark_mode", methods=["GET"])
def toggle_dark_mode():
    session["dark_mode"] = not session.get("dark_mode", False)
    return redirect(request.referrer or url_for("index"))


# Function to check allowed file extensions
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# Function to extract text from PDF using fitz
def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()  # Extract text from each page
    return text


# Function to generate a preview image for a PDF using fitz
def generate_pdf_preview(pdf_path, preview_filename):
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)  # Load the first page
    pix = page.get_pixmap()  # Get a Pixmap (image) of the page
    preview_image_path = os.path.join(app.config["PREVIEW_FOLDER"], preview_filename)
    pix.save(preview_image_path)  # Save the preview as a PNG image

    # Check if the preview file exists
    if os.path.exists(preview_image_path):
        return preview_image_path
    else:
        return None  # Return None if the preview couldn't be save


@app.route("/", methods=["GET", "POST"])
def index():
    filename = None
    if request.method == "POST":
        file = request.files.get("file")
        if file:
            filename = file.filename
    return render_template(
        "index.html", filename=filename, dark_mode=session.get("dark_mode", False)
    )


@app.route("/upload", methods=["GET", "POST"])
def upload_file():
    global uploads
    uploaded_filename = None
    preview_url = None
    extracted_text = None  # This will now contain JUST the summary
    message = None

    if request.method == "POST":
        if "file" in request.files:
            file = request.files["file"]

            if file.filename == "":
                return render_template(
                    "upload.html",
                    message="No selected file",
                    dark_mode=session.get("dark_mode", False),
                )

            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

                if any(upload["filename"] == filename for upload in uploads):
                    message = "This file has already been uploaded."
                    return render_template(
                        "upload.html", message=message, uploads=uploads
                    )

                file.save(file_path)
                raw_text = extract_text_from_pdf(file_path)

                # Generate and store ONLY the summary
                extracted_text = generate_summary(raw_text, tokenizer, model)
                extracted_text = format(extracted_text)
                extracted_text = format_for_html(extracted_text)

                text_filename = filename.replace(".pdf", ".txt")
                text_file_path = os.path.join(
                    app.config["EXTRACTED_FOLDER"], text_filename
                )

                with open(text_file_path, "w") as text_file:
                    text_file.write(extracted_text)  # Only save summary

                preview_filename = filename.replace(".pdf", ".png")
                generate_pdf_preview(file_path, preview_filename)
                preview_url = url_for("uploaded_preview", filename=preview_filename)
                uploaded_filename = filename

                uploads.append(
                    {
                        "filename": filename,
                        "preview_url": preview_url,
                        "text_filename": text_filename,
                    }
                )

        elif "view_extracted_text" in request.form:
            uploaded_filename = request.form["view_extracted_text"]
            text_filename = uploaded_filename.replace(".pdf", ".txt")
            text_file_path = os.path.join(app.config["EXTRACTED_FOLDER"], text_filename)

            for upload in uploads:
                if upload["filename"] == uploaded_filename:
                    preview_url = upload["preview_url"]
                    break

            with open(text_file_path, "r") as text_file:
                extracted_text = text_file.read()  # This reads just the summary

    return render_template(
        "upload.html",
        filename=uploaded_filename,
        extracted_text=extracted_text,  # This contains HTML if using Option 1
        preview_url=preview_url,
        uploads=uploads,
        message=message,
        dark_mode=session.get("dark_mode", False),
        is_html=request.form.get("html_view", False),  # Add this parameter
    )


# Route to serve uploaded PDF files
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# Route to serve extracted text files
@app.route("/extracted_text/<filename>")
def uploaded_text(filename):
    file_path = os.path.join(app.config["EXTRACTED_FOLDER"], filename)
    with open(file_path, "r") as file:
        extracted_text = file.read()
    return extracted_text


# Route to serve PDF preview images
@app.route("/previews/<filename>")
def uploaded_preview(filename):
    return send_from_directory(app.config["PREVIEW_FOLDER"], filename)


@app.route("/about")
def about():
    return render_template("about.html", dark_mode=session.get("dark_mode", False))


if __name__ == "__main__":
    app.run(port=5000,debug=False)
