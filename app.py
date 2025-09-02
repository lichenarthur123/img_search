#encoding=utf-8
from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
from werkzeug.utils import secure_filename
import threading
import json
#import cv2
#import numpy as np
from global_params import global_lock, global_variable
from search import search_similar_images
from flask import send_from_directory
from gevent import pywsgi

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB

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

@app.route('/batch_compare')
def batch_compare():
    return render_template('batch_compare.html')

@app.route('/batch_filter')
def batch_filter():
    return render_template('batch_filter.html')


@app.route('/cases')
def cases():
    return render_template('cases.html')

@app.route('/api/directory-structure')
def get_directory_structure():
    import os
    import json
    
    path = request.args.get('path', 'source')
    full_path = os.path.join(os.path.dirname(__file__), path)
    
    def build_tree(directory):
        node = {
            'name': os.path.basename(directory),
            'type': 'directory',
            'path': directory
        }
        
        children = []
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            if os.path.isdir(item_path):
                children.append(build_tree(item_path))
            else:
                children.append({
                    'name': item,
                    'type': 'file',
                    'path': item_path
                })
        
        node['children'] = children
        return node
    
    try:
        if not os.path.exists(full_path):
            return jsonify({'error': 'Directory not found'}), 404
        
        return jsonify(build_tree(full_path))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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


def load_database_data():
    """
    加载 database 目录下的数据到全局变量中
    """
    database_dir = 'database'
    if not os.path.exists(database_dir):
        print(f"Database directory {database_dir} does not exist.")
        return

    # 加载数据到全局变量
    with global_lock:
        global_variable['database_data'] = []
        for root, _, files in os.walk(database_dir):
            for file in files:
                if file == 'data.jsonl':
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r') as f:
                        for line in f:
                            try:
                                data = json.loads(line)
                                global_variable['database_data'].append(data)
                            except json.JSONDecodeError:
                                continue
        print(f"Loaded {len(global_variable['database_data'])} records from database.")


@app.route('/create_batch_compare_task', methods=['POST'])
def create_batch_compare_task():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Create batch_compare_task directory if not exists
    os.makedirs('batch_compare_task', exist_ok=True)

    # Generate a unique task directory name
    import random
    import string
    task_id = 'task_' + ''.join(random.choices(string.digits, k=8))
    task_dir = os.path.join('batch_compare_task', task_id)
    os.makedirs(task_dir, exist_ok=True)

    # Save the uploaded file as source.zip
    file_path = os.path.join(task_dir, 'source.zip')
    file.save(file_path)

    return jsonify({'task_id': task_id, 'message': 'Task created successfully'}), 200

@app.route('/get_batch_compare_status', methods=['GET'])
def get_batch_compare_status():
    task_status = []
    for task_id in os.listdir('batch_compare_task'):
        task_dir = os.path.join('batch_compare_task', task_id)
        if os.path.isdir(task_dir):
            result_file = os.path.join(task_dir, 'result.json')
            if os.path.exists(result_file):
                with open(result_file, 'r') as f:
                    json_data = json.load(f)
                    status = {
                        'task_id': task_id,
                        "progress": int(json_data['completed_tasks'] / json_data['total_tasks'] * 100),
                    }
                    xlsx_file = os.path.join(task_dir, 'result.xlsx')
                    if os.path.exists(xlsx_file):
                        status['xlsx_file'] = xlsx_file
                    
                    task_status.append(status)
    
    return jsonify(task_status)


#filter 
@app.route('/create_batch_filter_task', methods=['POST'])
def create_batch_filter_task():
    #task_name
    task_name = request.form.get('task_name', '')
    #if task_name == '':
    #    return jsonify({'error': 'No task name provided'}), 400

    # filterdesc
    filterdesc = request.form.get('filterdesc', '')
    if filterdesc == '':
        return jsonify({'error': 'No filter description provided'}), 400

    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Create batch_filter_task directory if not exists
    os.makedirs('batch_filter_task', exist_ok=True)

    # Generate a unique task directory name
    import random
    import string
    from datetime import datetime
    #task_id = task + task_name + timestamp_str
    task_id = f"{task_name}_task_" + datetime.now().strftime("%Y%m%d%H%M%S")
    #task_id = 'task_' + ''.join(random.choices(string.digits, k=8))
    task_dir = os.path.join('batch_filter_task', task_id)
    os.makedirs(task_dir, exist_ok=True)

    # Save the uploaded file as source.zip
    file_path = os.path.join(task_dir, 'source.zip')
    file.save(file_path)

    # Save the filter description to a file
    filterdesc_path = os.path.join(task_dir, 'prompt.txt')
    with open(filterdesc_path, 'w') as f:
        f.write(filterdesc)

    return jsonify({'task_id': task_id, 'message': 'Task created successfully'}), 200

@app.route('/get_batch_filter_status', methods=['GET'])
def get_batch_filter_status():
    task_status = []
    for task_id in os.listdir('batch_filter_task'):
        task_dir = os.path.join('batch_filter_task', task_id)
        if os.path.isdir(task_dir):
            DEL_FLAG = os.path.join(task_dir, 'DEL_FLAG')
            if os.path.exists(DEL_FLAG):
                continue
            result_file = os.path.join(task_dir, 'result.json')
            if os.path.exists(result_file):
                with open(result_file, 'r') as f:
                    json_data = json.load(f)
                    status = {
                        'task_id': task_id,
                        "progress": int(json_data['completed_tasks'] / json_data['total_tasks'] * 100),
                    }
                    #xlsx_file = os.path.join(task_dir, 'result.xlsx')
                    #if os.path.exists(xlsx_file):
                    #    status['xlsx_file'] = xlsx_file
                    #zip_file = os.path.join(task_dir, 'result.zip')
                    #if os.path.exists(zip_file):
                    #    status['results_file'] = zip_file
                    
                    task_status.append(status)
    return jsonify(task_status)

@app.route('/delete_filter_task', methods=['DELETE'])
def delete_filter_task():
    task_id = request.args.get('task_id')
    if not task_id:
        return jsonify({'error': 'Task ID is required'}), 400

    task_dir = os.path.join('batch_filter_task', task_id)
    if not os.path.isdir(task_dir):
        return jsonify({'error': 'Task not found'}), 404

    try:
        del_flag_path = os.path.join(task_dir, 'DEL_FLAG')
        with open(del_flag_path, 'w') as f:
            f.write('1')
        return jsonify({'message': 'Task deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download_result', methods=['GET'])
def download_result():
    task_id = request.args.get('task_id')
    if not task_id:
        return jsonify({'error': 'Task ID is required'}), 400

    task_dir = os.path.join('batch_filter_task', task_id)
    if not os.path.isdir(task_dir):
        return jsonify({'error': 'Task not found'}), 404

    xlsx_file = os.path.join(task_dir, 'result.xlsx')
    if not os.path.exists(xlsx_file):
        return jsonify({'error': 'Result file not found'}), 404

    return send_from_directory(task_dir, 'result.xlsx', as_attachment=True)

@app.route('/download_filter_result', methods=['GET'])
def download_filter_result():
    task_id = request.args.get('task_id')
    if not task_id:
        return jsonify({'error': 'Task ID is required'}), 400

    task_dir = os.path.join('batch_filter_task', task_id)
    if not os.path.isdir(task_dir):
        return jsonify({'error': 'Task not found'}), 404

    zip_file = os.path.join(task_dir, 'filtered_images.zip')
    if not os.path.exists(zip_file):
        return jsonify({'error': 'Result file not found'}), 404

    return send_from_directory(task_dir, 'filtered_images.zip', as_attachment=True)


if __name__ == '__main__':
    load_database_data()
    # 启动轮询线程
    from batch_task_manager import start_task_manager
    start_task_manager()
    server = pywsgi.WSGIServer(('0.0.0.0', 8080), app)
    #app.run(host="0.0.0.0", port=5000, debug=True)
    server.serve_forever()