import io
import os
import time
from flask import Flask, flash, redirect, render_template, request, send_file, url_for
from PIL import Image, UnidentifiedImageError
import pymongo
from stegano import lsb

app = Flask(__name__)

# Secret Key and Upload Folder
app.secret_key = os.getenv("FLASK_SECRET_KEY", b'_5#y2L"F4Q8z\n\xec]/')
UPLOAD_FOLDER = 'hidden_file'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit file size to 16MB

# Ensure upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://gyansanchar:gyansanchar@gyansanchar.z1gbmz8.mongodb.net/stegano")
client = pymongo.MongoClient(MONGO_URI)
mydb = client["mydatabase"]
mycollection = mydb["mycollection"]

# Allowed file types for images
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

# Routes
@app.route('/')
def index():
    return render_template('index.html', textIsHidden=False)

@app.route('/new_design')
def new_design():
    return render_template('new_index.html', textIsHidden=False)

@app.route('/text')
def text():
    return render_template('text.html', textIsHidden=False)

@app.route('/files')
def file():
    return render_template('file.html', textIsHidden=False)

@app.route('/audio')
def audio():
    return render_template('audio.html', textIsHidden=False)

@app.route('/video')
def video():
    return render_template('video.html', textIsHidden=False)

@app.route('/image')
def image():
    return render_template('image.html', textIsHidden=False)

@app.route("/encode", methods=['GET', 'POST'])
def encode():
    image_file = request.files.get("imageFileEncode")

    if not image_file or not allowed_file(image_file.filename):
        flash("Invalid image file. Please upload a valid PNG, JPG, or JPEG image.")
        return redirect("/")

    try:
        pil_image = Image.open(image_file.stream)
    except UnidentifiedImageError:
        flash("Uploaded file is not a valid image.")
        return redirect("/")

    timestamp = str(int(time.time()))
    file_to_hide = request.files.get('fileToHide')
    text_to_hide = request.form.get('textToHide')
    encode_password = request.form.get('encodePassword')

    if not encode_password:
        flash("Password is required!")
        return redirect("/")

    collection_data = {'timestamp': timestamp, 'password': encode_password}
    if file_to_hide:
        new_filename = f"{timestamp}_{file_to_hide.filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
        file_to_hide.save(file_path)

        collection_data['type'] = 'file'
        collection_data['data'] = file_path
        collection_data['mimetype'] = file_to_hide.mimetype
    elif text_to_hide:
        collection_data['type'] = 'text'
        collection_data['data'] = text_to_hide
    else:
        flash("No text or file provided to hide.")
        return redirect("/")

    secret = lsb.hide(pil_image, timestamp)
    imgByteArr = io.BytesIO()
    secret.save(imgByteArr, format='PNG')
    imgByteArr.seek(0)

    mycollection.insert_one(collection_data)

    return send_file(
        imgByteArr,
        mimetype='image/png',
        as_attachment=True,
        download_name=f"encoded_{image_file.filename}"
    )

@app.route("/decode", methods=['GET', 'POST'])
def decode():
    image_file = request.files.get("imageFileDecode")
    
    if not image_file or not allowed_file(image_file.filename):
        flash("Invalid image file. Please upload a valid PNG, JPG, or JPEG image.")
        return redirect("/")

    try:
        pil_image = Image.open(image_file.stream)
    except UnidentifiedImageError:
        flash("Uploaded file is not a valid image.")
        return redirect("/")

    try:
        timestamp_ = lsb.reveal(pil_image)
    except Exception as e:
        flash("Unable to decode the image.")
        return redirect("/")

    encode_password = request.form.get('encodePassword')

    if not encode_password:
        flash("Password is required!")
        return redirect("/")

    data = mycollection.find_one({"timestamp": timestamp_, "password": encode_password})

    if not data:
        flash("Either invalid file or incorrect password.")
        return redirect("/")

    if data['type'] == "text":
        return render_template('text.html', textIsHidden=True, hiddenText=data['data'])

    return send_file(
        data['data'],
        mimetype=data['mimetype'],
        as_attachment=True,
        download_name=f"decoded_{'_'.join(data['data'].split('_')[1:])}"
    )

if __name__ == "__main__":
    app.run(debug=True)
