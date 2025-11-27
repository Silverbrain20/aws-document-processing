from flask import Flask, render_template, request, jsonify
import boto3
import json
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def index():
    return '''
<!DOCTYPE html>
<html>
<head><title>AWS IDP System</title></head>
<body>
    <h1>Document Processing System</h1>
    <form id="uploadForm" enctype="multipart/form-data">
        <input type="file" id="fileInput" accept=".pdf,.jpg,.png">
        <button type="submit">Upload & Process</button>
    </form>
    <div id="results"></div>
    
    <h2>Processed Documents</h2>
    <div id="documents"></div>
    
    <script>
        document.getElementById('uploadForm').onsubmit = async (e) => {
            e.preventDefault();
            const file = document.getElementById('fileInput').files[0];
            if (!file) return;
            
            const formData = new FormData();
            formData.append('file', file);
            
            const response = await fetch('/upload', {method: 'POST', body: formData});
            const result = await response.json();
            document.getElementById('results').innerHTML = '<pre>' + JSON.stringify(result, null, 2) + '</pre>';
            loadDocuments();
        };
        
        async function loadDocuments() {
            const response = await fetch('/documents');
            const docs = await response.json();
            document.getElementById('documents').innerHTML = docs.map(doc => 
                '<div><strong>' + doc.document_id + '</strong><br>' + 
                (doc.extracted_text || 'Processing...') + '</div>'
            ).join('<hr>');
        }
        
        loadDocuments();
    </script>
</body>
</html>'''

@app.route('/upload', methods=['POST'])
def upload():
    try:
        file = request.files['file']
        s3 = boto3.client('s3', region_name='us-east-1')
        
        # Upload to S3
        bucket = 'aws-idp-raw-774305598371-dev'
        key = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
        s3.upload_fileobj(file, bucket, key)
        
        # Process with Textract
        textract = boto3.client('textract', region_name='us-east-1')
        response = textract.detect_document_text(
            Document={'S3Object': {'Bucket': bucket, 'Name': key}}
        )
        
        text = ' '.join([block['Text'] for block in response['Blocks'] if block['BlockType'] == 'LINE'])
        
        # Store in DynamoDB
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.Table('aws-idp-documents-dev')
        table.put_item(Item={
            'document_id': key,
            'extracted_text': text,
            'status': 'completed',
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return jsonify({'status': 'success', 'document_id': key, 'text': text[:500]})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/documents')
def documents():
    try:
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.Table('aws-idp-documents-dev')
        response = table.scan()
        return jsonify(response['Items'])
    except Exception as e:
        return jsonify([])

if __name__ == '__main__':
    app.run(debug=True, port=5000)