#!/usr/bin/env python3
"""
Demo script to test all file transfer functionality
"""

import os
import sys
import threading
import time
import subprocess
from client import FileTransferClient

def create_large_test_file():
    """Create a large test file (>1MB) to demonstrate chunking"""
    server_dir = 'server_files'
    if not os.path.exists(server_dir):
        os.makedirs(server_dir)
    
    # Create a file larger than 1MB to test chunking
    large_file_path = os.path.join(server_dir, 'large_test_file.txt')
    if not os.path.exists(large_file_path):
        print("Creating large test file (>1MB) for chunking demonstration...")
        with open(large_file_path, 'w') as f:
            # Write about 1.5MB of data
            for i in range(50000):
                f.write(f"This is line {i+1} of the large test file. " * 3 + "\n")
        print(f"Created large test file: {os.path.getsize(large_file_path)} bytes")

def run_server():
    """Run the server in a separate process"""
    print("Starting server...")
    server_process = subprocess.Popen([sys.executable, 'server.py'], 
                                     stdout=subprocess.PIPE, 
                                     stderr=subprocess.PIPE)
    time.sleep(2)  # Give server time to start
    return server_process

def demo_client_functionality():
    """Demonstrate all client functionality"""
    print("\n" + "="*60)
    print("DEMONSTRATION OF FILE TRANSFER APPLICATION")
    print("="*60)
    
    # Wait for server to start
    time.sleep(3)
    
    client = FileTransferClient()
    
    print("\n1. CONNECTING TO SERVER")
    print("-" * 30)
    if not client.connect():
        print("Failed to connect to server!")
        return
    
    print("\n2. LISTING AVAILABLE FILES")
    print("-" * 30)
    files = client.list_files()
    
    if not files:
        print("No files available for demonstration")
        client.disconnect()
        return
    
    print("\n3. SINGLE FILE DOWNLOAD DEMONSTRATION")
    print("-" * 40)
    print(f"Downloading first file: {files[0]['name']}")
    success = client.download_file(files[0]['name'])
    if success:
        print("✓ Single file download completed successfully!")
    else:
        print("✗ Single file download failed!")
    
    if len(files) >= 2:
        print("\n4. MULTIPLE FILE DOWNLOAD DEMONSTRATION")
        print("-" * 42)
        selected_files = [f['name'] for f in files[:min(3, len(files))]]
        print(f"Downloading multiple files: {', '.join(selected_files)}")
        success = client.download_multiple_files(selected_files)
        if success:
            print("✓ Multiple file download completed successfully!")
        else:
            print("✗ Multiple file download failed!")
    
    print("\n5. VERIFYING DOWNLOADED FILES")
    print("-" * 32)
    download_dir = client.download_directory
    if os.path.exists(download_dir):
        downloaded_files = os.listdir(download_dir)
        print(f"Files in download directory ({download_dir}):")
        for filename in downloaded_files:
            filepath = os.path.join(download_dir, filename)
            size = os.path.getsize(filepath)
            print(f"  - {filename}: {size} bytes")
    
    client.disconnect()
    
    print("\n" + "="*60)
    print("DEMONSTRATION COMPLETED!")
    print("="*60)

def main():
    # Create test files
    create_large_test_file()
    
    print("Starting File Transfer Application Demo...")
    print("This demo will automatically test all features:")
    print("- Multi-client server")
    print("- Directory listing")
    print("- Single file download")
    print("- Multiple file download")
    print("- File chunking (for files >1MB)")
    print("- Progress tracking")
    
    # Start server in background
    server_process = run_server()
    
    try:
        # Run client demo
        demo_client_functionality()
    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
    finally:
        # Clean up server process
        print("\nShutting down server...")
        server_process.terminate()
        server_process.wait()
        print("Server shut down.")

if __name__ == "__main__":
    main() 