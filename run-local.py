#!/usr/bin/env python3
"""
Local development server for the web UI
"""

from modern-app import app
import os

if __name__ == '__main__':
    print("🚀 Starting AWS IDP Web UI")
    print("📱 Mobile optimized interface")
    print("🌐 Open: http://localhost:5000")
    print("=" * 40)
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )