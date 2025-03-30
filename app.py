import os
import subprocess
import sys
import stat
from werkzeug.serving import is_running_from_reloader

REQUIRED_PACKAGES = [
    "Flask==2.0.1",
    "flask-cors==3.0.10",
    "fitz==1.18.14",
    "language_tool_python==2.7.1",
    "transformers==4.12.3",
    "torch==1.9.0",
    "requests==2.26.0",
    "gunicorn==20.1.0",
    "Werkzeug==2.0.1",  # This provides is_running_from_reloader
]


# Add this function to check if server is already running
def is_server_running():
    try:
        import requests

        return requests.get("http://localhost:5000/health").status_code == 200
    except:
        return False


def install_missing_packages():
    for package in REQUIRED_PACKAGES:
        try:
            __import__(package.split("==")[0].lower())
            print(f"✓ {package} already installed")
        except ImportError:
            print(f"Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])


from flask import (
    Flask,
    request,
    render_template,
    send_from_directory,
    url_for,
    session,
    redirect,
    jsonify,
)
import fitz

app = Flask(__name__)
app.secret_key = os.urandom(24)


@app.route("/health")
def health_check():
    return {"status": "healthy"}, 200


# Set the upload folder
UPLOAD_FOLDER = "uploads/"
EXTRACTED_FOLDER = "extracted_text/"
PREVIEW_FOLDER = "previews"
ALLOWED_EXTENSIONS = {"pdf"}

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
    formatted_text = format(text)
    html_text = formatted_text.replace("\n\n", "</p><p>").replace("\n", "<br>")
    return f"<p>{html_text}</p>"


@app.route("/toggle_dark_mode", methods=["GET"])
def toggle_dark_mode():
    session["dark_mode"] = not session.get("dark_mode", False)
    return redirect(request.referrer or url_for("index"))


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text


def generate_pdf_preview(pdf_path, preview_filename):
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    pix = page.get_pixmap()
    preview_image_path = os.path.join(app.config["PREVIEW_FOLDER"], preview_filename)
    pix.save(preview_image_path)
    return preview_image_path if os.path.exists(preview_image_path) else None


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
    file_name = None
    preview_url = None
    extracted_text = None
    message = None

    if request.method == "POST":
        if "file" in request.files:
            file = request.files["file"]

            if file and allowed_file(file.filename):
                filename = file.filename
                file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

                # Save and process the file only if it's not a duplicate
                if not any(upload["filename"] == filename for upload in uploads):
                    file.save(file_path)

                    # Extract and summarize text immediately
                    raw_text = extract_text_from_pdf(file_path)
                    extracted_text = generate_summary(raw_text, tokenizer, model)
                    extracted_text = format_for_html(extracted_text)

                    # Save the extracted text to a file
                    text_filename = filename.replace(".pdf", ".txt")
                    with open(
                        os.path.join(app.config["EXTRACTED_FOLDER"], text_filename), "w"
                    ) as f:
                        f.write(extracted_text)

                    # Generate PDF preview
                    preview_filename = filename.replace(".pdf", ".png")
                    generate_pdf_preview(file_path, preview_filename)
                    preview_url = url_for("uploaded_preview", filename=preview_filename)

                    # Append the upload info to the list
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
            with open(
                os.path.join(app.config["EXTRACTED_FOLDER"], text_filename), "r"
            ) as f:
                extracted_text = f.read()

    # Render the page with extracted text immediately
    return render_template(
        "upload.html",
        filename=uploaded_filename,
        extracted_text=extracted_text,
        preview_url=preview_url,
        uploads=uploads,
        message=message,
        dark_mode=session.get("dark_mode", False),
    )


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/extracted_text/<filename>")
def uploaded_text(filename):
    with open(os.path.join(app.config["EXTRACTED_FOLDER"], filename), "r") as f:
        return f.read()


@app.route("/previews/<filename>")
def uploaded_preview(filename):
    return send_from_directory(app.config["PREVIEW_FOLDER"], filename)


@app.route("/about")
def about():
    return render_template("about.html", dark_mode=session.get("dark_mode", False))


def make_executable():
    script_path = os.path.join(os.path.dirname(__file__), "launch_server.py")
    st = os.stat(script_path)
    os.chmod(script_path, st.st_mode | stat.S_IEXEC)


if __name__ == "__main__":
    if not is_server_running():  # Only start if not already running
        install_missing_packages()
        from model import initialize_summarizer, generate_summary, format

        tokenizer, model = initialize_summarizer()

        print("Starting Flask server...")
        app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
