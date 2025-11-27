#!/bin/bash

# AWS IDP System Web UI Startup Script

echo "Starting AWS IDP System Web UI..."

# Set environment variables
export AWS_REGION=${AWS_REGION:-us-east-1}
export ENVIRONMENT=${ENVIRONMENT:-dev}
export FLASK_APP=app.py
export FLASK_ENV=development

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check AWS credentials
echo "Checking AWS credentials..."
aws sts get-caller-identity > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ AWS credentials not configured. Please run 'aws configure'"
    exit 1
fi

echo "✅ AWS credentials configured"

# Start Flask application
echo "Starting Flask application on http://localhost:5000"
echo "Press Ctrl+C to stop"
python app.py