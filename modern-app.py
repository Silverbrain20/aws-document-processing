from flask import Flask, render_template, request, jsonify
import boto3
import json
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('modern-index.html')

@app.route('/upload', methods=['POST'])
def upload():
    try:
        file = request.files['file']
        s3 = boto3.client('s3', region_name='us-east-1')
        
        bucket = 'aws-idp-raw-774305598371-dev'
        key = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
        s3.upload_fileobj(file, bucket, key)
        
        textract = boto3.client('textract', region_name='us-east-1')
        response = textract.detect_document_text(
            Document={'S3Object': {'Bucket': bucket, 'Name': key}}
        )
        
        text = ' '.join([block['Text'] for block in response['Blocks'] if block['BlockType'] == 'LINE'])
        
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.Table('aws-idp-documents-dev')
        table.put_item(Item={
            'document_id': key,
            'extracted_text': text,
            'status': 'completed',
            'timestamp': datetime.utcnow().isoformat(),
            'filename': file.filename
        })
        
        return jsonify({
            'status': 'success', 
            'document_id': key, 
            'text': text[:500],
            'filename': file.filename,
            'word_count': len(text.split())
        })
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