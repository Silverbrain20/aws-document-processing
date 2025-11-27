#!/usr/bin/env python3
"""
Simple Flask web UI for testing AWS IDP system
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
import boto3
import json
import uuid
import time
from datetime import datetime
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# AWS Configuration
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
ACCOUNT_ID = boto3.client('sts').get_caller_identity()['Account']

# AWS Resources
RAW_BUCKET = f'aws-idp-system-documents-raw-{ACCOUNT_ID}-{ENVIRONMENT}'
STATE_MACHINE_ARN = f'arn:aws:states:{AWS_REGION}:{ACCOUNT_ID}:stateMachine:aws-idp-system-document-processing-{ENVIRONMENT}'
METADATA_TABLE = f'aws-idp-system-document-metadata-{ENVIRONMENT}'

# Initialize AWS clients
s3_client = boto3.client('s3', region_name=AWS_REGION)
stepfunctions_client = boto3.client('stepfunctions', region_name=AWS_REGION)
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)

@app.route('/')
def index():
    """Main page with upload form"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_document():
    """Handle document upload and start processing"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file selected'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        document_type = request.form.get('document_type', 'general')
        
        # Generate unique document ID
        document_id = f"web-{uuid.uuid4()}"
        filename = secure_filename(file.filename)
        s3_key = f"web-uploads/{document_id}_{filename}"
        
        # Upload to S3
        s3_client.put_object(
            Bucket=RAW_BUCKET,
            Key=s3_key,
            Body=file.read(),
            Metadata={
                'document_type': document_type,
                'original_filename': filename,
                'upload_source': 'web_ui'
            }
        )
        
        # Start Step Functions execution
        execution_input = {
            'document_id': document_id,
            'source_bucket': RAW_BUCKET,
            'source_key': s3_key
        }
        
        response = stepfunctions_client.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            name=f"web-execution-{document_id}",
            input=json.dumps(execution_input)
        )
        
        return jsonify({
            'success': True,
            'document_id': document_id,
            'execution_arn': response['executionArn'],
            'message': 'Document uploaded and processing started'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/status/<document_id>')
def get_status(document_id):
    """Get processing status for a document"""
    try:
        table = dynamodb.Table(METADATA_TABLE)
        response = table.get_item(Key={'document_id': document_id})
        
        if 'Item' in response:
            item = response['Item']
            return jsonify({
                'document_id': document_id,
                'status': item.get('status', 'unknown'),
                'confidence_score': float(item.get('metadata', {}).get('final_confidence_score', 0)),
                'processing_time': item.get('total_processing_time_ms', 0),
                'document_type': item.get('metadata', {}).get('document_type', 'unknown'),
                'updated_timestamp': item.get('updated_timestamp', ''),
                'has_results': item.get('status') == 'completed'
            })
        else:
            return jsonify({
                'document_id': document_id,
                'status': 'not_found',
                'message': 'Document not found or processing not started'
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/results/<document_id>')
def get_results(document_id):
    """Get extraction results for a document"""
    try:
        results_table = dynamodb.Table(f'aws-idp-system-extraction-results-{ENVIRONMENT}')
        
        # Get final results
        response = results_table.get_item(
            Key={
                'document_id': document_id,
                'extraction_type': 'final_results'
            }
        )
        
        if 'Item' in response:
            results = response['Item']['results']
            return jsonify({
                'document_id': document_id,
                'raw_text': results.get('raw_text', ''),
                'entities': results.get('entities', []),
                'tables': results.get('table_content', ''),
                'forms': results.get('form_fields', {}),
                'confidence_score': float(results.get('confidence_score', 0)),
                'document_type': results.get('document_type', 'unknown'),
                'page_count': results.get('page_count', 0),
                'has_tables': results.get('has_tables', False),
                'has_forms': results.get('has_forms', False),
                'has_signatures': results.get('has_signatures', False)
            })
        else:
            return jsonify({
                'document_id': document_id,
                'error': 'Results not found or processing not completed'
            }), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/documents')
def list_documents():
    """List recent documents"""
    try:
        table = dynamodb.Table(METADATA_TABLE)
        
        # Scan recent documents (in production, use GSI with pagination)
        response = table.scan(
            Limit=20,
            FilterExpression='attribute_exists(upload_timestamp)'
        )
        
        documents = []
        for item in response.get('Items', []):
            documents.append({
                'document_id': item['document_id'],
                'status': item.get('status', 'unknown'),
                'upload_timestamp': item.get('upload_timestamp', ''),
                'confidence_score': float(item.get('metadata', {}).get('final_confidence_score', 0)),
                'document_type': item.get('metadata', {}).get('document_type', 'unknown')
            })
        
        # Sort by upload timestamp (newest first)
        documents.sort(key=lambda x: x['upload_timestamp'], reverse=True)
        
        return jsonify({'documents': documents})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/dashboard')
def dashboard():
    """Dashboard page showing recent documents"""
    return render_template('dashboard.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)