from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import cv2
import numpy as np
import base64
import io
import os
from PIL import Image
import pyttsx3
import threading
from ultralytics import YOLO
from datetime import datetime
import json

app = Flask(__name__)
CORS(app)

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
RESULTS_FOLDER = 'results'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(RESULTS_FOLDER):
    os.makedirs(RESULTS_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULTS_FOLDER'] = RESULTS_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Load YOLO model
model = YOLO("best.pt")

# Define classes
CLASSES = {
    0: 'Hardhat', 1: 'Mask', 2: 'NO-Hardhat', 3: 'NO-Mask', 
    4: 'NO-Safety Vest', 5: 'Person', 6: 'Safety Cone', 
    7: 'Safety Vest', 8: 'machinery', 9: 'vehicle'
}

# Define safety violations
SAFETY_VIOLATIONS = ['NO-Hardhat', 'NO-Mask', 'NO-Safety Vest']

def speak_result(text):
    """Function to speak the result using text-to-speech"""
    try:
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print(f"TTS Error: {e}")

def detect_objects(image_path):
    """Detect objects in the image and return results"""
    # Read image
    image = cv2.imread(image_path)
    if image is None:
        return None, "Error: Could not read image"
    
    # Resize image for consistent processing
    image = cv2.resize(image, (1020, 600))
    
    # Run detection
    detections = model(image)
    
    results = {
        'violations': [],
        'all_detections': [],
        'safety_status': 'SAFE',
        'confidence_scores': [],
        'image_dimensions': image.shape[:2]
    }
    
    # Process detections
    for detection in detections:
        # Filter detections by confidence threshold
        filtered_detections = detection.boxes[detection.boxes.conf >= 0.3]
        
        if len(filtered_detections) > 0:
            class_ids = filtered_detections.cls.tolist()
            confidences = filtered_detections.conf.tolist()
            boxes = filtered_detections.xyxy.tolist()
            
            for i, class_id in enumerate(class_ids):
                class_id = int(class_id)
                class_name = CLASSES.get(class_id, 'Unknown')
                confidence = confidences[i]
                box = boxes[i]
                
                detection_info = {
                    'class_name': class_name,
                    'confidence': round(confidence, 2),
                    'bbox': [round(coord) for coord in box]
                }
                
                results['all_detections'].append(detection_info)
                results['confidence_scores'].append(round(confidence, 2))
                
                # Check for safety violations
                if class_name in SAFETY_VIOLATIONS:
                    results['violations'].append(detection_info)
                    results['safety_status'] = 'VIOLATION DETECTED'
    
    # Draw bounding boxes on image
    annotated_image = draw_annotations(image, results)
    
    # Save annotated image
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_image_path = os.path.join(app.config['RESULTS_FOLDER'], f"result_{timestamp}.jpg")
    cv2.imwrite(result_image_path, annotated_image)
    
    return results, result_image_path

def draw_annotations(image, results):
    """Draw bounding boxes and labels on the image"""
    annotated_image = image.copy()
    
    for detection in results['all_detections']:
        class_name = detection['class_name']
        confidence = detection['confidence']
        bbox = detection['bbox']
        
        x1, y1, x2, y2 = bbox
        
        # Choose color based on safety status
        if class_name in SAFETY_VIOLATIONS:
            color = (0, 0, 255)  # Red for violations
        else:
            color = (0, 255, 0)  # Green for safe equipment
        
        # Draw bounding box
        cv2.rectangle(annotated_image, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
        
        # Draw label
        label = f"{class_name}: {confidence:.2f}"
        label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
        cv2.rectangle(annotated_image, (int(x1), int(y1) - label_size[1] - 10), 
                     (int(x1) + label_size[0], int(y1)), color, -1)
        cv2.putText(annotated_image, label, (int(x1), int(y1) - 5), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
    
    return annotated_image

def generate_safety_message(results):
    """Generate safety message based on detection results"""
    violations = results['violations']
    
    if not violations:
        return "All safety equipment detected. Workplace is safe!"
    
    messages = []
    violation_types = set()
    
    for violation in violations:
        violation_types.add(violation['class_name'])
    
    for violation_type in violation_types:
        if violation_type == 'NO-Hardhat':
            messages.append("SAFETY VIOLATION: Hard hat not detected. Please wear a hard hat.")
        elif violation_type == 'NO-Mask':
            messages.append("SAFETY VIOLATION: Face mask not detected. Please wear a face mask.")
        elif violation_type == 'NO-Safety Vest':
            messages.append("SAFETY VIOLATION: Safety vest not detected. Please wear a safety vest.")
    
    return " ".join(messages)

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and process PPE detection"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        # Save uploaded file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"upload_{timestamp}_{file.filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Process the image
        results, result_image_path = detect_objects(filepath)
        
        if results is None:
            return jsonify({'error': result_image_path}), 500
        
        # Generate safety message
        safety_message = generate_safety_message(results)
        
        # Start TTS in a separate thread
        if request.form.get('enable_audio') == 'true':
            tts_thread = threading.Thread(target=speak_result, args=(safety_message,))
            tts_thread.daemon = True
            tts_thread.start()
        
        # Convert result image to base64 for display
        with open(result_image_path, 'rb') as img_file:
            img_base64 = base64.b64encode(img_file.read()).decode('utf-8')
        
        response = {
            'success': True,
            'safety_status': results['safety_status'],
            'safety_message': safety_message,
            'violations_count': len(results['violations']),
            'total_detections': len(results['all_detections']),
            'detections': results['all_detections'],
            'violations': results['violations'],
            'result_image': img_base64,
            'timestamp': timestamp
        }
        
        return jsonify(response)
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/camera')
def camera_page():
    """Camera capture page"""
    return render_template('camera.html')

@app.route('/results')
def results_page():
    """Results history page"""
    return render_template('results.html')

def allowed_file(filename):
    """Check if the uploaded file is allowed"""
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Starting PPE Detection Server...")
    print("=" * 50)
    print("📍 Access the application at:")
    print("   🌐 http://localhost:5000")
    print("   🌐 http://127.0.0.1:5000")
    print("=" * 50)
    print("✨ Features:")
    print("   📤 Image Upload & Analysis")
    print("   📹 Live Camera Detection")
    print("   📊 Results Dashboard")
    print("   🔊 Audio Alerts")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)