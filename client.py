#!/usr/bin/env python3
"""
File Transfer Client
Supports downloading single/multiple files with progress tracking
"""

import socket
import json
import os
import time
from typing import List

class FileTransferClient:
    def __init__(self, host='localhost', port=8888, download_directory='downloads'):
        self.host = host
        self.port = port
        self.download_directory = download_directory
        self.buffer_size = 4096
        self.socket = None
        
        # Create download directory if it doesn't exist
        if not os.path.exists(self.download_directory):
            os.makedirs(self.download_directory)
            print(f"Created download directory: {self.download_directory}")
    
    def connect(self):
        """Connect to the server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            print(f"Connected to server at {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"Failed to connect to server: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the server"""
        if self.socket:
            try:
                disconnect_cmd = {'type': 'disconnect'}
                self.send_message(json.dumps(disconnect_cmd))
                self.socket.close()
                print("Disconnected from server")
            except:
                pass
    
    def send_message(self, message):
        """Send a message with length prefix"""
        message_bytes = message.encode('utf-8')
        length_bytes = len(message_bytes).to_bytes(4, byteorder='big')
        self.socket.send(length_bytes + message_bytes)
    
    def receive_message(self):
        """Receive a message with length prefix"""
        try:
            # First receive the length of the message
            length_data = self.socket.recv(4)
            if not length_data:
                return None
            
            message_length = int.from_bytes(length_data, byteorder='big')
            
            # Then receive the actual message
            message_data = b''
            while len(message_data) < message_length:
                chunk = self.socket.recv(min(message_length - len(message_data), self.buffer_size))
                if not chunk:
                    return None
                message_data += chunk
            
            return message_data.decode('utf-8')
        except:
            return None
    
    def list_files(self):
        """Request and display list of available files from server"""
        try:
            list_cmd = {'type': 'list_files'}
            self.send_message(json.dumps(list_cmd))
            
            response_data = self.receive_message()
            if not response_data:
                print("No response from server")
                return []
            
            response = json.loads(response_data)
            
            if response['type'] == 'error':
                print(f"Error: {response['message']}")
                return []
            
            files = response['files']
            
            if not files:
                print("No files available on the server")
                return []
            
            print("\nAvailable files on server:")
            print("-" * 60)
            print(f"{'#':<3} {'Filename':<30} {'Size (MB)':<10} {'Size (bytes)':<15}")
            print("-" * 60)
            
            for i, file_info in enumerate(files, 1):
                print(f"{i:<3} {file_info['name']:<30} {file_info['size_mb']:<10} {file_info['size']:<15}")
            
            print("-" * 60)
            return files
            
        except Exception as e:
            print(f"Error listing files: {e}")
            return []
    
    def download_file(self, filename):
        """Download a single file from the server"""
        try:
            download_cmd = {
                'type': 'download_file',
                'filename': filename
            }
            self.send_message(json.dumps(download_cmd))
            
            # First, receive file info
            response_data = self.receive_message()
            if not response_data:
                print("No response from server")
                return False
            
            response = json.loads(response_data)
            
            if response['type'] == 'error':
                print(f"Error: {response['message']}")
                return False
            
            if response['type'] != 'file_info':
                print("Unexpected response from server")
                return False
            
            filename = response['filename']
            file_size = response['file_size']
            num_chunks = response['num_chunks']
            
            print(f"\nDownloading {filename} ({file_size} bytes, {num_chunks} chunks)")
            
            # Prepare file for writing
            filepath = os.path.join(self.download_directory, filename)
            
            with open(filepath, 'wb') as f:
                total_received = 0
                
                for chunk_num in range(num_chunks):
                    # Receive chunk info
                    chunk_info_data = self.receive_message()
                    if not chunk_info_data:
                        print("Failed to receive chunk info")
                        return False
                    
                    chunk_info = json.loads(chunk_info_data)
                    chunk_size = chunk_info['chunk_size']
                    chunk_number = chunk_info['chunk_number']
                    
                    # Receive chunk data
                    chunk_data = b''
                    while len(chunk_data) < chunk_size:
                        remaining = chunk_size - len(chunk_data)
                        data = self.socket.recv(min(remaining, self.buffer_size))
                        if not data:
                            print("Connection lost during file transfer")
                            return False
                        chunk_data += data
                    
                    f.write(chunk_data)
                    total_received += len(chunk_data)
                    
                    # Calculate and display progress
                    progress = (total_received / file_size) * 100
                    print(f"Downloading {filename} part {chunk_number} .... {progress:.1f}%")
            
            # Receive completion message
            completion_data = self.receive_message()
            if completion_data:
                completion = json.loads(completion_data)
                if completion['type'] == 'file_complete':
                    print(f"✓ Successfully downloaded {filename}")
                    return True
            
            return False
            
        except Exception as e:
            print(f"Error downloading file: {e}")
            return False
    
    def download_multiple_files(self, filenames):
        """Download multiple files from the server"""
        try:
            download_cmd = {
                'type': 'download_multiple',
                'filenames': filenames
            }
            self.send_message(json.dumps(download_cmd))
            
            # Receive start message
            response_data = self.receive_message()
            if not response_data:
                print("No response from server")
                return False
            
            response = json.loads(response_data)
            
            if response['type'] == 'error':
                print(f"Error: {response['message']}")
                return False
            
            if response['type'] != 'multiple_transfer_start':
                print("Unexpected response from server")
                return False
            
            total_files = response['total_files']
            print(f"\nStarting download of {total_files} files...")
            
            # Download each file
            for file_index in range(total_files):
                print(f"\n--- File {file_index + 1}/{total_files} ---")
                
                # The server will send each file using the same protocol as single file download
                # We need to handle file_info, chunks, and completion for each file
                
                # Receive file info
                file_info_data = self.receive_message()
                if not file_info_data:
                    print("Failed to receive file info")
                    return False
                
                file_info = json.loads(file_info_data)
                
                if file_info['type'] == 'error':
                    print(f"Error: {file_info['message']}")
                    continue
                
                filename = file_info['filename']
                file_size = file_info['file_size']
                num_chunks = file_info['num_chunks']
                
                print(f"Downloading {filename} ({file_size} bytes, {num_chunks} chunks)")
                
                # Download file chunks
                filepath = os.path.join(self.download_directory, filename)
                
                with open(filepath, 'wb') as f:
                    total_received = 0
                    
                    for chunk_num in range(num_chunks):
                        # Receive chunk info
                        chunk_info_data = self.receive_message()
                        if not chunk_info_data:
                            print("Failed to receive chunk info")
                            break
                        
                        chunk_info = json.loads(chunk_info_data)
                        chunk_size = chunk_info['chunk_size']
                        chunk_number = chunk_info['chunk_number']
                        
                        # Receive chunk data
                        chunk_data = b''
                        while len(chunk_data) < chunk_size:
                            remaining = chunk_size - len(chunk_data)
                            data = self.socket.recv(min(remaining, self.buffer_size))
                            if not data:
                                print("Connection lost during file transfer")
                                break
                            chunk_data += data
                        
                        f.write(chunk_data)
                        total_received += len(chunk_data)
                        
                        # Calculate and display progress
                        progress = (total_received / file_size) * 100
                        print(f"Downloading {filename} part {chunk_number} .... {progress:.1f}%")
                
                # Receive file completion message
                completion_data = self.receive_message()
                if completion_data:
                    completion = json.loads(completion_data)
                    if completion['type'] == 'file_complete':
                        print(f"✓ Successfully downloaded {filename}")
            
            # Receive overall completion message
            final_completion_data = self.receive_message()
            if final_completion_data:
                final_completion = json.loads(final_completion_data)
                if final_completion['type'] == 'multiple_transfer_complete':
                    print(f"\n✓ Successfully downloaded all {total_files} files!")
                    return True
            
            return False
            
        except Exception as e:
            print(f"Error downloading multiple files: {e}")
            return False

def show_menu():
    """Display the main menu"""
    print("\n" + "="*50)
    print("File Transfer Client")
    print("="*50)
    print("1. List available files")
    print("2. Download single file")
    print("3. Download multiple files")
    print("4. Exit")
    print("="*50)

def main():
    client = FileTransferClient()
    
    if not client.connect():
        return
    
    try:
        while True:
            show_menu()
            choice = input("Enter your choice (1-4): ").strip()
            
            if choice == '1':
                client.list_files()
            
            elif choice == '2':
                files = client.list_files()
                if files:
                    try:
                        file_index = int(input(f"\nEnter file number (1-{len(files)}): ")) - 1
                        if 0 <= file_index < len(files):
                            filename = files[file_index]['name']
                            client.download_file(filename)
                        else:
                            print("Invalid file number")
                    except ValueError:
                        filename = input("Enter filename: ").strip()
                        if filename:
                            client.download_file(filename)
            
            elif choice == '3':
                files = client.list_files()
                if files:
                    print("\nEnter file numbers separated by commas (e.g., 1,2,3):")
                    try:
                        indices_input = input("File numbers: ").strip()
                        indices = [int(x.strip()) - 1 for x in indices_input.split(',')]
                        
                        filenames = []
                        for idx in indices:
                            if 0 <= idx < len(files):
                                filenames.append(files[idx]['name'])
                            else:
                                print(f"Warning: Invalid file number {idx + 1}, skipping")
                        
                        if filenames:
                            print(f"Selected files: {', '.join(filenames)}")
                            confirm = input("Proceed with download? (y/n): ").strip().lower()
                            if confirm in ['y', 'yes']:
                                client.download_multiple_files(filenames)
                        else:
                            print("No valid files selected")
                    except ValueError:
                        print("Invalid input format")
            
            elif choice == '4':
                break
            
            else:
                print("Invalid choice. Please enter 1-4.")
    
    except KeyboardInterrupt:
        print("\nClient interrupted by user")
    
    finally:
        client.disconnect()

if __name__ == "__main__":
    main() 