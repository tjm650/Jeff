#/usr/bin/env python3
"""
Script to start Django development server with ngrok tunneling.
Usage: python start_with_ngrok.py [ngrok_auth_token]
"""

import os
import sys
import subprocess
import time
from threading import Thread
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def run_ngrok_tunnel(auth_token=None):
    """Run ngrok tunnel in a separate thread."""
    if auth_token:
        print(f"Starting ngrok tunnel with auth token...")
        os.environ['NGROK_AUTH_TOKEN'] = auth_token
    else:
        print("Starting ngrok tunnel...")

    os.environ['USE_NGROK'] = 'true'

    print("Starting Django development server with ngrok integration...")
    try:
        subprocess.run([sys.executable, 'manage.py', 'runserver', '127.0.0.1:8000'])
    except KeyboardInterrupt:
        print("\nShutting down ngrok tunnel...")
        try:
            from pyngrok import ngrok
            ngrok.kill()
        except ImportError:
            print("pyngrok not installed")

if __name__ == '__main__':
    # Check for ngrok auth token as command line argument
    auth_token = None
    if len(sys.argv) > 1:
        auth_token = sys.argv[1]

    print("=== Django + Ngrok Development Server ===")
    print("Press Ctrl+C to stop both servers")

    try:
        run_ngrok_tunnel(auth_token)
    except KeyboardInterrupt:
        print("\nShutting down...")
        try:
            from pyngrok import ngrok
            ngrok.kill()
            print("Ngrok tunnel closed.")
        except ImportError:
            print("pyngrok not installed")