from flask import Flask, render_template, request, jsonify
import boto3
import json
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def index():
    return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AWS Document Processing</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50">
    <div class="container mx-auto px-4 py-8">
        <div class="max-w-2xl mx-auto bg-white rounded-lg shadow p-6">
            <h1 class="text-2xl font-bold mb-6">AWS Document Processing</h1>
            
            <form id="uploadForm" enctype="multipart/form-data" class="space-y-4">
                <div class="border-2 border-dashed border-blue-300 rounded-lg p-8 text-center">
                    <input type="file" id="fileInput" accept=".pdf,.jpg,.png" class="mb-4">
                    <button type="submit" class="bg-blue-600 text-white px-6 py-2 rounded">
                        Process with Textract
                    </button>
                </div>
            </form>
            
            <div id="results" class="mt-6 hidden">
                <h3 class="font-bold mb-2">Extraction Results:</h3>
                <div id="output" class="bg-gray-100 p-4 rounded max-h-64 overflow-y-auto"></div>
            </div>
        </div>
    </div>
    
    <script>
        document.getElementById('uploadForm').onsubmit = async (e) => {
            e.preventDefault();
            const file = document.getElementById('fileInput').files[0];
            if (!file) return alert('Select a file');
            
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                const response = await fetch('/upload', {method: 'POST', body: formData});
                const result = await response.json();
                
                document.getElementById('results').classList.remove('hidden');
                document.getElementById('output').innerHTML = 
                    '<strong>Status:</strong> ' + result.status + '<br>' +
                    '<strong>Text:</strong><br>' + (result.text || 'No text extracted');
            } catch (error) {
                alert('Error: ' + error.message);
            }
        };
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
        
        # Call Lambda function
        lambda_client = boto3.client('lambda', region_name='us-east-1')
        response = lambda_client.invoke(
            FunctionName='aws-idp-processing',
            Payload=json.dumps({'bucket': bucket, 'key': key})
        )
        
        result = json.loads(response['Payload'].read())
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=5000)