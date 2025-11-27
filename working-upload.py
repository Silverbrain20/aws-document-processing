#!/usr/bin/env python3
"""
Working Flask app for document upload testing - no Unicode issues
"""

from flask import Flask, request, jsonify
import boto3
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# AWS setup
sts = boto3.client('sts')
account_id = sts.get_caller_identity()['Account']
bucket_name = f'aws-idp-system-documents-raw-{account_id}-dev'

@app.route('/')
def index():
    return f'''
<!DOCTYPE html>
<html>
<head>
    <title>AWS IDP Upload Test</title>
    <style>
        body {{ font-family: Arial; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
        .upload-box {{ 
            border: 3px dashed #007bff; 
            padding: 40px; 
            text-align: center; 
            margin: 20px 0;
            cursor: pointer;
            border-radius: 10px;
        }}
        .upload-box:hover {{ background-color: #f0f8ff; }}
        button {{ 
            background: #007bff; 
            color: white; 
            padding: 12px 24px; 
            border: none; 
            cursor: pointer; 
            border-radius: 5px;
            font-size: 16px;
        }}
        button:hover {{ background: #0056b3; }}
        .status {{ 
            margin: 20px 0; 
            padding: 15px; 
            border-radius: 5px;
            display: none;
        }}
        .success {{ background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }}
        .error {{ background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }}
        .info {{ background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>AWS IDP Document Upload</h1>
        <p><strong>Bucket:</strong> {bucket_name}</p>
        
        <form id="uploadForm" enctype="multipart/form-data">
            <div class="upload-box" onclick="document.getElementById('fileInput').click()">
                <h3>Click to Select File</h3>
                <p>Supports: PDF, JPG, PNG, TIFF</p>
                <input type="file" id="fileInput" name="file" style="display:none" 
                       accept=".pdf,.jpg,.jpeg,.png,.tiff,.bmp">
            </div>
            
            <div style="margin: 20px 0;">
                <label><strong>Document Type:</strong></label><br>
                <select name="document_type" style="padding: 8px; width: 200px; margin-top: 5px;">
                    <option value="general">General Document</option>
                    <option value="invoice">Invoice</option>
                    <option value="medical">Medical Record</option>
                    <option value="contract">Contract</option>
                </select>
            </div>
            
            <div id="selectedFile" style="margin: 15px 0; font-weight: bold;"></div>
            
            <button type="submit" id="uploadBtn">Upload Document</button>
        </form>
        
        <div id="status" class="status"></div>
        
        <div style="margin-top: 30px; padding: 15px; background: #f8f9fa; border-radius: 5px;">
            <h4>Test Status:</h4>
            <p>[OK] S3 Bucket: Ready</p>
            <p>[OK] Upload Endpoint: Active</p>
            <p>[INFO] Processing Pipeline: Not deployed (upload only)</p>
        </div>
    </div>

    <script>
        const fileInput = document.getElementById('fileInput');
        const selectedFile = document.getElementById('selectedFile');
        const uploadForm = document.getElementById('uploadForm');
        const status = document.getElementById('status');
        const uploadBtn = document.getElementById('uploadBtn');
        
        fileInput.addEventListener('change', function() {{
            if (this.files.length > 0) {{
                const file = this.files[0];
                selectedFile.innerHTML = `Selected: ${{file.name}} (${{(file.size/1024/1024).toFixed(2)}} MB)`;
            }}
        }});
        
        uploadForm.addEventListener('submit', async function(e) {{
            e.preventDefault();
            
            if (fileInput.files.length === 0) {{
                showStatus('Please select a file first!', 'error');
                return;
            }}
            
            uploadBtn.disabled = true;
            uploadBtn.innerHTML = 'Uploading...';
            showStatus('Uploading file to S3...', 'info');
            
            const formData = new FormData(uploadForm);
            
            try {{
                const response = await fetch('/upload', {{
                    method: 'POST',
                    body: formData
                }});
                
                const result = await response.json();
                
                if (result.success) {{
                    showStatus(`[SUCCESS] Upload successful!<br>
                               Document ID: ${{result.document_id}}<br>
                               Bucket: ${{result.bucket}}<br>
                               Key: ${{result.key}}`, 'success');
                }} else {{
                    showStatus(`[ERROR] Upload failed: ${{result.error}}`, 'error');
                }}
            }} catch (error) {{
                showStatus(`[ERROR] Network error: ${{error.message}}`, 'error');
            }} finally {{
                uploadBtn.disabled = false;
                uploadBtn.innerHTML = 'Upload Document';
            }}
        }});
        
        function showStatus(message, type) {{
            status.className = `status ${{type}}`;
            status.innerHTML = message;
            status.style.display = 'block';
        }}
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
        document_id = f"upload-{uuid.uuid4()}"
        filename = secure_filename(file.filename)
        s3_key = f"uploads/{document_id}_{filename}"
        
        # Upload to S3
        s3_client = boto3.client('s3')
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=file.read(),
            Metadata={
                'document_type': document_type,
                'original_filename': filename,
                'upload_source': 'web_ui'
            }
        )
        
        return jsonify({
            'success': True,
            'document_id': document_id,
            'bucket': bucket_name,
            'key': s3_key,
            'message': 'File uploaded successfully to S3'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'bucket': bucket_name,
        'account_id': account_id
    })

if __name__ == '__main__':
    print("Starting AWS IDP Upload Server...")
    print(f"URL: http://localhost:5000")
    print(f"S3 Bucket: {bucket_name}")
    print("Press Ctrl+C to stop")
    app.run(debug=True, host='0.0.0.0', port=5000)