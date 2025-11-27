#!/usr/bin/env python3
"""
Simple test Flask app for AWS IDP system
"""

from flask import Flask, render_template, request, jsonify
import boto3
import json
import uuid
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Test AWS connection
try:
    sts = boto3.client('sts')
    account_id = sts.get_caller_identity()['Account']
    print(f"[OK] AWS connected - Account: {account_id}")
except Exception as e:
    print(f"[ERROR] AWS connection failed: {e}")
    account_id = "000000000000"

@app.route('/')
def index():
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>AWS IDP Test</title>
    <style>
        body { font-family: Arial; margin: 40px; }
        .upload-area { 
            border: 2px dashed #007bff; 
            padding: 40px; 
            text-align: center; 
            margin: 20px 0;
            cursor: pointer;
        }
        .upload-area:hover { background-color: #f0f8ff; }
        button { 
            background: #007bff; 
            color: white; 
            padding: 10px 20px; 
            border: none; 
            cursor: pointer; 
        }
        .status { margin: 20px 0; padding: 10px; background: #f8f9fa; }
    </style>
</head>
<body>
    <h1>AWS IDP System Test</h1>
    
    <form id="uploadForm" enctype="multipart/form-data">
        <div class="upload-area" onclick="document.getElementById('fileInput').click()">
            <p>Click to select file or drag & drop</p>
            <input type="file" id="fileInput" name="file" style="display:none" 
                   accept=".pdf,.jpg,.jpeg,.png,.tiff">
        </div>
        
        <div>
            <label>Document Type:</label>
            <select name="document_type">
                <option value="general">General</option>
                <option value="invoice">Invoice</option>
                <option value="medical">Medical</option>
            </select>
        </div>
        
        <div id="selectedFile" style="margin: 10px 0;"></div>
        
        <button type="submit">Upload & Process</button>
    </form>
    
    <div id="status" class="status" style="display:none;"></div>
    <div id="results" style="display:none;"></div>

    <script>
        const fileInput = document.getElementById('fileInput');
        const selectedFile = document.getElementById('selectedFile');
        const uploadForm = document.getElementById('uploadForm');
        const status = document.getElementById('status');
        
        fileInput.addEventListener('change', function() {
            if (this.files.length > 0) {
                selectedFile.innerHTML = `Selected: ${this.files[0].name}`;
            }
        });
        
        uploadForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            if (fileInput.files.length === 0) {
                alert('Please select a file');
                return;
            }
            
            status.style.display = 'block';
            status.innerHTML = 'Uploading...';
            
            const formData = new FormData(uploadForm);
            
            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    status.innerHTML = `[OK] Upload successful! Document ID: ${result.document_id}`;
                } else {
                    status.innerHTML = `[ERROR] Upload failed: ${result.error}`;
                }
            } catch (error) {
                status.innerHTML = `[ERROR] Error: ${error.message}`;
            }
        });
    </script>
</body>
</html>
    '''

@app.route('/upload', methods=['POST'])
def upload_document():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file selected'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        document_type = request.form.get('document_type', 'general')
        document_id = f"test-{uuid.uuid4()}"
        filename = secure_filename(file.filename)
        
        # Test S3 upload
        try:
            s3_client = boto3.client('s3')
            bucket_name = f'aws-idp-system-documents-raw-{account_id}-dev'
            s3_key = f"test-uploads/{document_id}_{filename}"
            
            s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=file.read(),
                Metadata={
                    'document_type': document_type,
                    'original_filename': filename,
                    'upload_source': 'test_ui'
                }
            )
            
            return jsonify({
                'success': True,
                'document_id': document_id,
                'bucket': bucket_name,
                'key': s3_key,
                'message': 'File uploaded to S3 successfully'
            })
            
        except Exception as s3_error:
            return jsonify({
                'error': f'S3 upload failed: {str(s3_error)}',
                'bucket_attempted': f'aws-idp-system-documents-raw-{account_id}-dev'
            }), 500
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/test')
def test_aws():
    """Test AWS connectivity"""
    results = {}
    
    # Test STS
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        results['sts'] = f"[OK] Connected as {identity.get('Arn', 'Unknown')}"
    except Exception as e:
        results['sts'] = f"[ERROR] Failed: {e}"
    
    # Test S3
    try:
        s3 = boto3.client('s3')
        buckets = s3.list_buckets()
        bucket_count = len(buckets['Buckets'])
        results['s3'] = f"[OK] Connected - {bucket_count} buckets accessible"
    except Exception as e:
        results['s3'] = f"[ERROR] Failed: {e}"
    
    return jsonify(results)

if __name__ == '__main__':
    print("Starting AWS IDP Test Server...")
    print("Visit: http://localhost:5000")
    print("Test AWS: http://localhost:5000/test")
    app.run(debug=True, host='0.0.0.0', port=5000)