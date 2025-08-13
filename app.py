from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
from werkzeug.utils import secure_filename
#import cv2
import numpy as np
from search import search_similar_images

from flask import send_from_directory

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Store image descriptions and paths
image_database = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/update')
def update():
    return render_template('update.html')

@app.route('/compare')
def compare():
    return render_template('compare.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'images' not in request.files:
        return redirect(request.url)
    
    files = request.files.getlist('images')
    description = request.form.get('description', '')
    
    # Create a random directory
    import random
    import string
    while True:
        random_dir = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        source_dir = os.path.join('source', random_dir)
        if not os.path.exists(source_dir):
            os.makedirs(source_dir)
            break
    
    # Save description to desc.txt
    with open(os.path.join(source_dir, 'desc.txt'), 'w') as f:
        f.write(description)

    # Save images with numeric names
    for idx, file in enumerate(files):
        if file.filename == '':
            continue
        
        if file and allowed_file(file.filename):
            file_ext = os.path.splitext(file.filename)[1]
            filepath = os.path.join(source_dir, f"{idx}{file_ext}")
            file.save(filepath)
            
            # Store image info (limit to 10 images per instance)
            if len(image_database) < 10:
                image_database.append({
                    'path': filepath,
                    'description': description
                })
    
    # 调用embedding.py处理图片
    from embedding import process_directory
    process_directory(source_dir)
    
    return redirect(url_for('index'))


    if 'image' not in request.files:
        return redirect(request.url)
    
    file = request.files['image']
    
    if file.filename == '':
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Calculate similarity with stored images
        similarities = []
        for img_data in image_database:
            similarity = calculate_similarity(filepath, img_data['path'])
            similarities.append({
                'path': img_data['path'],
                'description': img_data['description'],
                'similarity': similarity
            })
        
        # Sort by similarity
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        
        return render_template('result.html', similarities=similarities)
    
    return redirect(request.url)

@app.route('/source/<path:subdir>/<filename>')
def serve_file(subdir, filename):
    target_dir = os.path.join('source', subdir)
    # 安全校验：目录必须在根目录内
    if not os.path.abspath(target_dir).startswith(os.path.abspath('source')):
        abort(403, "Forbidden: Path traversal attempt")
    
    # 仅允许图片文件（按需扩展）
    if not filename.lower().endswith(('.png', '.jpg', '.jpeg', '.txt')):
        abort(403, "File type not allowed")
    
    return send_from_directory(target_dir, filename)

@app.route('/search', methods=['POST'])
def handle_search():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400
    
    image_file = request.files['image']
    database_dir = request.form.get('database_dir', 'database')
    
    # Save the uploaded image temporarily
    temp_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(image_file.filename))
    image_file.save(temp_path)
    
    # Read the image as binary data
    #with open(temp_path, 'rb') as f:
    #    image_bytes = f.read()
    
    # Call the search method
    results = search_similar_images(temp_path, database_dir)
    
    # Clean up the temporary file
    os.remove(temp_path)
    
    return jsonify(results)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}


if __name__ == '__main__':
    app.run(debug=True)