#!/usr/bin/env python3
"""
File Transfer Server
Supports multiple clients, file chunking, and directory listing
"""

import socket
import threading
import os
import json
import time
from typing import List, Dict

class FileTransferServer:
    def __init__(self, host='localhost', port=8888, server_directory='server_files'):
        self.host = host
        self.port = port
        self.server_directory = server_directory
        self.chunk_size = 1024 * 1024  # 1MB chunks
        self.buffer_size = 4096
        
        # Create server directory if it doesn't exist
        if not os.path.exists(self.server_directory):
            os.makedirs(self.server_directory)
            print(f"Created server directory: {self.server_directory}")
    
    def start_server(self):
        """Start the server and listen for connections"""
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((self.host, self.port))
            server_socket.listen(5)
            
            print(f"Server started on {self.host}:{self.port}")
            print(f"Server directory: {os.path.abspath(self.server_directory)}")
            print("Waiting for connections...")
            
            while True:
                client_socket, client_address = server_socket.accept()
                print(f"Connection established with {client_address}")
                
                # Handle each client in a separate thread
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_address)
                )
                client_thread.daemon = True
                client_thread.start()
                
        except Exception as e:
            print(f"Server error: {e}")
        finally:
            server_socket.close()
    
    def handle_client(self, client_socket, client_address):
        """Handle individual client connections"""
        try:
            while True:
                # Receive command from client
                command_data = self.receive_message(client_socket)
                if not command_data:
                    break
                
                command = json.loads(command_data)
                cmd_type = command.get('type')
                
                if cmd_type == 'list_files':
                    self.send_file_list(client_socket)
                
                elif cmd_type == 'download_file':
                    filename = command.get('filename')
                    self.send_file(client_socket, filename)
                
                elif cmd_type == 'download_multiple':
                    filenames = command.get('filenames')
                    self.send_multiple_files(client_socket, filenames)
                
                elif cmd_type == 'disconnect':
                    break
                
        except Exception as e:
            print(f"Error handling client {client_address}: {e}")
        finally:
            client_socket.close()
            print(f"Connection with {client_address} closed")
    
    def receive_message(self, client_socket):
        """Receive a message with length prefix"""
        try:
            # First receive the length of the message
            length_data = client_socket.recv(4)
            if not length_data:
                return None
            
            message_length = int.from_bytes(length_data, byteorder='big')
            
            # Then receive the actual message
            message_data = b''
            while len(message_data) < message_length:
                chunk = client_socket.recv(min(message_length - len(message_data), self.buffer_size))
                if not chunk:
                    return None
                message_data += chunk
            
            return message_data.decode('utf-8')
        except:
            return None
    
    def send_message(self, client_socket, message):
        """Send a message with length prefix"""
        message_bytes = message.encode('utf-8')
        length_bytes = len(message_bytes).to_bytes(4, byteorder='big')
        client_socket.send(length_bytes + message_bytes)
    
    def send_file_list(self, client_socket):
        """Send list of available files to client"""
        try:
            files = []
            for filename in os.listdir(self.server_directory):
                filepath = os.path.join(self.server_directory, filename)
                if os.path.isfile(filepath):
                    file_size = os.path.getsize(filepath)
                    files.append({
                        'name': filename,
                        'size': file_size,
                        'size_mb': round(file_size / (1024 * 1024), 2)
                    })
            
            response = {
                'type': 'file_list',
                'files': files
            }
            
            self.send_message(client_socket, json.dumps(response))
            print(f"Sent file list with {len(files)} files")
            
        except Exception as e:
            error_response = {
                'type': 'error',
                'message': f"Error listing files: {str(e)}"
            }
            self.send_message(client_socket, json.dumps(error_response))
    
    def send_file(self, client_socket, filename):
        """Send a single file to client with chunking support"""
        try:
            filepath = os.path.join(self.server_directory, filename)
            
            if not os.path.exists(filepath):
                error_response = {
                    'type': 'error',
                    'message': f"File '{filename}' not found"
                }
                self.send_message(client_socket, json.dumps(error_response))
                return
            
            file_size = os.path.getsize(filepath)
            
            # Calculate number of chunks needed
            num_chunks = (file_size + self.chunk_size - 1) // self.chunk_size
            
            # Send file metadata
            file_info = {
                'type': 'file_info',
                'filename': filename,
                'file_size': file_size,
                'num_chunks': num_chunks,
                'chunk_size': self.chunk_size
            }
            self.send_message(client_socket, json.dumps(file_info))
            
            # Send file chunks
            with open(filepath, 'rb') as f:
                for chunk_num in range(num_chunks):
                    chunk_data = f.read(self.chunk_size)
                    
                    chunk_info = {
                        'type': 'file_chunk',
                        'chunk_number': chunk_num + 1,
                        'total_chunks': num_chunks,
                        'chunk_size': len(chunk_data)
                    }
                    
                    # Send chunk metadata
                    self.send_message(client_socket, json.dumps(chunk_info))
                    
                    # Send chunk data
                    client_socket.send(chunk_data)
                    
                    print(f"Sent chunk {chunk_num + 1}/{num_chunks} of {filename}")
                    time.sleep(0.1)  # Small delay to prevent overwhelming the client
            
            # Send completion message
            completion_msg = {
                'type': 'file_complete',
                'filename': filename
            }
            self.send_message(client_socket, json.dumps(completion_msg))
            print(f"File '{filename}' sent successfully")
            
        except Exception as e:
            error_response = {
                'type': 'error',
                'message': f"Error sending file: {str(e)}"
            }
            self.send_message(client_socket, json.dumps(error_response))
    
    def send_multiple_files(self, client_socket, filenames):
        """Send multiple files to client"""
        try:
            # Send start message for multiple file transfer
            start_msg = {
                'type': 'multiple_transfer_start',
                'total_files': len(filenames),
                'filenames': filenames
            }
            self.send_message(client_socket, json.dumps(start_msg))
            
            # Send each file
            for i, filename in enumerate(filenames):
                print(f"Sending file {i+1}/{len(filenames)}: {filename}")
                self.send_file(client_socket, filename)
            
            # Send completion message
            completion_msg = {
                'type': 'multiple_transfer_complete',
                'total_files': len(filenames)
            }
            self.send_message(client_socket, json.dumps(completion_msg))
            print(f"Multiple file transfer completed: {len(filenames)} files sent")
            
        except Exception as e:
            error_response = {
                'type': 'error',
                'message': f"Error in multiple file transfer: {str(e)}"
            }
            self.send_message(client_socket, json.dumps(error_response))

def main():
    # Create some sample files for testing
    server_dir = 'server_files'
    if not os.path.exists(server_dir):
        os.makedirs(server_dir)
    
    # Create sample files with different sizes
    sample_files = [
        ('small_file.txt', 'This is a small test file.\n' * 100),
        ('medium_file.txt', 'This is a medium test file.\n' * 10000),
        ('large_file.txt', 'This is a large test file.\n' * 100000),
    ]
    
    for filename, content in sample_files:
        filepath = os.path.join(server_dir, filename)
        if not os.path.exists(filepath):
            with open(filepath, 'w') as f:
                f.write(content)
            print(f"Created sample file: {filename}")
    
    # Start the server
    server = FileTransferServer()
    try:
        server.start_server()
    except KeyboardInterrupt:
        print("\nServer shutting down...")

if __name__ == "__main__":
    main() 