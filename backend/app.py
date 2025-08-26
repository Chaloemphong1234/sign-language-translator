from flask import Flask, request, jsonify
import tensorflow as tf
import numpy as np
from PIL import Image
import io
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# =========================
# กำหนดขนาดภาพให้ตรงกับโมเดลที่เทรน
IMG_WIDTH, IMG_HEIGHT = 160, 160
MODEL_PATH = 'models/sign_model.h5'

# โหลดโมเดล
try:
    model = tf.keras.models.load_model(MODEL_PATH)
    print("Model loaded successfully.")
except Exception as e:
    print(f"Error loading model: {e}")
    model = None

# โหลด label จากโฟลเดอร์ dataset
class_labels = sorted(os.listdir('dataset/train')) if os.path.exists('dataset/train') else []
print(f"Class labels: {class_labels}")

# หน้าเช็กสถานะ API
@app.route('/')
def index():
    return '''
    <h1>Sign Language Prediction API</h1>
    <p>API is running successfully.</p>
    <p>Go to <a href="/upload">/upload</a> to test image upload.</p>
    '''

# หน้าเว็บสำหรับอัปโหลดภาพ
@app.route('/upload', methods=['GET'])
def upload_form():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Sign Language Prediction</title>
    </head>
    <body>
        <h2>Upload an Image for Prediction</h2>
        <form action="/predict" method="post" enctype="multipart/form-data">
            <input type="file" name="file" required>
            <br><br>
            <input type="submit" value="Predict">
        </form>
    </body>
    </html>
    '''

# API ทำนายภาพ
@app.route('/predict', methods=['POST'])
def predict():
    if model is None:
        return jsonify({'error': 'Model not loaded'}), 500

    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    try:
        # โหลดและแปลงภาพเป็น RGB
        image = Image.open(io.BytesIO(file.read())).convert('RGB')
        # Resize ให้ตรงกับโมเดล
        image = image.resize((IMG_WIDTH, IMG_HEIGHT))
        # แปลงเป็น array และ normalize
        image_array = np.array(image) / 255.0
        # เพิ่ม batch dimension
        image_array = np.expand_dims(image_array, axis=0)
    except Exception as e:
        return jsonify({'error': f'Invalid image data: {str(e)}'}), 400

    # ทำนาย
    prediction = model.predict(image_array)
    predicted_class_index = np.argmax(prediction)
    predicted_label = class_labels[predicted_class_index] if class_labels else str(predicted_class_index)

    return jsonify({
        'prediction': predicted_label,
        'confidence': float(np.max(prediction))
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
