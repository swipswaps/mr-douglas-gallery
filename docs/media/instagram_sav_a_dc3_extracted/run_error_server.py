#!/usr/bin/env python3
"""
HTTP server for receiving browser error logs
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import sys
from datetime import datetime
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path.cwd()))

from db_logger import init_error_db

class ErrorCollectionHandler(BaseHTTPRequestHandler):
    """HTTP handler that receives browser error logs"""
    
    conn = None
    
    def log_message(self, format, *args):
        """Suppress default HTTP server logs"""
        pass
    
    def do_POST(self):
        """Handle POST requests from browser error logging"""
        if self.path == '/log_error':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                error_data = json.loads(post_data.decode('utf-8'))
                
                if ErrorCollectionHandler.conn:
                    cursor = ErrorCollectionHandler.conn.cursor()
                    cursor.execute('''
                        INSERT INTO browser_errors (timestamp, error_type, error_message, source, lineno, colno, stack_trace)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        datetime.now().isoformat(),
                        error_data.get('type', 'unknown'),
                        error_data.get('message', ''),
                        error_data.get('source', ''),
                        error_data.get('lineno', 0),
                        error_data.get('colno', 0),
                        error_data.get('stack', '')
                    ))
                    ErrorCollectionHandler.conn.commit()
                    print(f"[Browser Error] {error_data.get('type')}: {error_data.get('message', '')[:100]}")
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'ok'}).encode())
                
            except Exception as e:
                print(f"Error processing browser log: {e}")
                self.send_response(500)
                self.end_headers()
        
        elif self.path == '/log_console':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                log_data = json.loads(post_data.decode('utf-8'))
                
                if ErrorCollectionHandler.conn:
                    cursor = ErrorCollectionHandler.conn.cursor()
                    cursor.execute('''
                        INSERT INTO browser_console_logs (timestamp, log_level, message, source_info)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        datetime.now().isoformat(),
                        log_data.get('level', 'log'),
                        log_data.get('message', ''),
                        log_data.get('source', '')
                    ))
                    ErrorCollectionHandler.conn.commit()
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'ok'}).encode())
                
            except Exception as e:
                print(f"Error processing browser log: {e}")
                self.send_response(500)
                self.end_headers()
        
        elif self.path == '/log_image':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                image_data = json.loads(post_data.decode('utf-8'))
                
                if ErrorCollectionHandler.conn:
                    cursor = ErrorCollectionHandler.conn.cursor()
                    cursor.execute('''
                        INSERT INTO image_load_attempts (timestamp, image_url, success, error_message, http_status)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        datetime.now().isoformat(),
                        image_data.get('url', ''),
                        1 if image_data.get('success') else 0,
                        image_data.get('error', ''),
                        image_data.get('status', 0)
                    ))
                    ErrorCollectionHandler.conn.commit()
                
                self.send_response(200)
                self.end_headers()
                
            except Exception as e:
                self.send_response(500)
                self.end_headers()
        
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode())
        else:
            self.send_response(404)
            self.end_headers()

def start_error_server(conn, port=8001):
    """Start the error collection HTTP server"""
    ErrorCollectionHandler.conn = conn
    server = HTTPServer(('localhost', port), ErrorCollectionHandler)
    print(f"[Error Server] Listening on http://localhost:{port}")
    server.serve_forever()

if __name__ == "__main__":
    print("=" * 50)
    print("ERROR COLLECTION SERVER")
    print("=" * 50)
    print("Starting Error Collection Server...")
    conn = init_error_db()
    print(f"Database initialized at: gallery_errors.db")
    print(f"Error server running on http://localhost:8001")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    
    try:
        start_error_server(conn, 8001)
    except KeyboardInterrupt:
        print("\nShutting down error server...")
        conn.close()
        sys.exit(0)