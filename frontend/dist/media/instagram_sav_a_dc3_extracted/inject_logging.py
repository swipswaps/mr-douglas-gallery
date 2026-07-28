#!/usr/bin/env python3
"""
inject_logging.py - Adds logging to working v0013 gallery WITHOUT breaking it

UPGRADED VERSION v2:
- Fixed BrokenPipeError with try-except around response writing
- Injects client-side error capture script into HTML
- Thread-safe database access with check_same_thread=False
- Handles HEAD requests properly
- Sets correct Content-Type for JSON responses
- Database write fallback with in-memory queue and retry logic
- SIGTERM signal handling for graceful shutdown
- AUTO PORT SELECTION (finds available port if 8000 is busy)
- Better error recovery for database locks
"""

import http.server
import socketserver
import threading
import webbrowser
import json
import sqlite3
import signal
import os
import sys
import time
import random
from datetime import datetime
from pathlib import Path

DB_PATH = Path("gallery_errors.db")
INJECTION_SCRIPT = '''
<!-- Logging Injection Script -->
<script>
(function() {
    var logQueue = [];
    var flushInterval = null;
    
    function sendEvents() {
        if (logQueue.length === 0) return;
        var events = logQueue.slice();
        logQueue = [];
        try {
            var xhr = new XMLHttpRequest();
            xhr.open('POST', '/log_event', true);
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.send(JSON.stringify({events: events, batch: true}));
        } catch(e) {
            console.warn('Batch logging failed:', e);
            logQueue = events.concat(logQueue);
        }
    }
    
    function logEvent(type, data) {
        var event = {
            type: type,
            data: data,
            url: window.location.href,
            timestamp: new Date().toISOString(),
            userAgent: navigator.userAgent
        };
        logQueue.push(event);
        if (!flushInterval) {
            flushInterval = setInterval(sendEvents, 2000);
        }
        if (logQueue.length >= 10) sendEvents();
    }
    
    window.logEvent = logEvent;
    
    window.addEventListener('error', function(e) {
        logEvent('js_error', {
            message: e.message,
            filename: e.filename,
            lineno: e.lineno,
            colno: e.colno,
            stack: e.error ? e.error.stack : null
        });
    });
    
    window.addEventListener('unhandledrejection', function(e) {
        logEvent('promise_rejection', {
            reason: String(e.reason),
            stack: e.reason && e.reason.stack ? e.reason.stack : null
        });
    });
    
    var originalConsoleError = console.error;
    console.error = function() {
        var args = Array.prototype.slice.call(arguments);
        logEvent('console_error', args.map(String).join(' '));
        originalConsoleError.apply(console, args);
    };
    
    document.addEventListener('click', function(e) {
        var target = e.target;
        var card = target.closest('.card');
        if (card) {
            var shortcode = card.dataset.shortcode;
            if (shortcode) {
                logEvent('gallery_click', { shortcode: shortcode, target: target.tagName });
            }
        }
    });
    
    window.addEventListener('load', function() {
        var perfData = performance.timing;
        var loadTime = perfData.loadEventEnd - perfData.navigationStart;
        logEvent('page_load', { loadTimeMs: loadTime, url: window.location.href });
    });
    
    console.log('[Logging] Client-side error capture active');
})();
</script>
'''

def init_db():
    """Initialize database with thread-safe mode and retry logic"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10.0)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS page_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    event_type TEXT,
                    event_data TEXT,
                    page_url TEXT,
                    user_agent TEXT
                )
            ''')
            # Add index for faster queries
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_event_type ON page_events(event_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON page_events(timestamp)')
            conn.commit()
            print(f"✓ Database initialized: {DB_PATH}")
            return conn
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                print(f"⚠️ Database locked, retrying in 1s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(1)
            else:
                print(f"✗ Database error: {e}")
                raise
    return None

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """Handle multiple requests concurrently"""
    allow_reuse_address = True
    daemon_threads = True

class LoggingHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler that injects logging script and captures events"""
    
    conn = None
    _queue = []
    _queue_lock = threading.Lock()
    _batch_buffer = []
    _batch_lock = threading.Lock()
    protocol_version = 'HTTP/1.1'
    
    def log_message(self, format, *args):
        """Suppress default logs"""
        pass
    
    def do_HEAD(self):
        """Handle HEAD requests gracefully"""
        self.send_response(200)
        self.end_headers()
    
    def do_GET(self):
        # Handle logging endpoint
        if self.path == '/log_event':
            self.handle_log_event()
            return
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
            return
        
        # Handle normal file requests with HTML injection
        if self.path == '/' or self.path == '/index_v0013.html' or self.path == '/index_v0021.html':
            self.path = '/index_v0021.html'  # Use v0021 by default
            self.serve_injected_html()
        else:
            self.serve_normal_file()
    
    def do_POST(self):
        """Handle POST requests (for logging)"""
        if self.path == '/log_event':
            self.handle_log_event()
        else:
            self.send_response(404)
            self.end_headers()
    
    def handle_log_event(self):
        """Process incoming log events with batch support"""
        content_length = int(self.headers.get('Content-Length', 0))
        events_processed = 0
        
        if content_length > 0:
            try:
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                
                # Handle batch events
                if data.get('batch'):
                    events = data.get('events', [])
                    for event in events:
                        if self._write_event_to_db(event, self.headers.get('User-Agent', '')):
                            events_processed += 1
                else:
                    # Single event
                    if self._write_event_to_db(data, self.headers.get('User-Agent', '')):
                        events_processed = 1
                        
            except json.JSONDecodeError as e:
                print(f"[Log Error] Invalid JSON: {e}")
            except Exception as e:
                print(f"[Log Error] {e}")
        
        # Send response
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        try:
            self.wfile.write(json.dumps({'status': 'ok', 'processed': events_processed}).encode())
        except (BrokenPipeError, ConnectionResetError):
            pass
    
    def _write_event_to_db(self, event, user_agent):
        """Write a single event to database with retry"""
        max_retries = 2
        for attempt in range(max_retries):
            try:
                if LoggingHandler.conn:
                    cursor = LoggingHandler.conn.cursor()
                    cursor.execute('''
                        INSERT INTO page_events (timestamp, event_type, event_data, page_url, user_agent)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        event.get('timestamp', datetime.now().isoformat()),
                        event.get('type', 'unknown'),
                        json.dumps(event.get('data', {})),
                        event.get('url', ''),
                        user_agent
                    ))
                    LoggingHandler.conn.commit()
                    print(f"[Event] {event.get('type')}: {str(event.get('data', ''))[:80]}")
                    return True
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    time.sleep(0.1)
                    continue
                print(f"[DB Error] {e}, queuing for later")
                with LoggingHandler._queue_lock:
                    LoggingHandler._queue.append({
                        'timestamp': event.get('timestamp', datetime.now().isoformat()),
                        'type': event.get('type', 'unknown'),
                        'data': event.get('data', {}),
                        'url': event.get('url', ''),
                        'user_agent': user_agent
                    })
                return False
            except Exception as e:
                print(f"[DB Error] {e}")
                return False
        return False
    
    def serve_injected_html(self):
        """Serve HTML with injected logging script"""
        try:
            html_path = self.find_html_file()
            if not html_path:
                self.send_error(404, "HTML file not found")
                return
            
            with open(html_path, 'rb') as f:
                content = f.read().decode('utf-8', errors='replace')
            
            # Inject script before </body>
            if '</body>' in content:
                content = content.replace('</body>', INJECTION_SCRIPT + '</body>')
            elif '</html>' in content:
                content = content.replace('</html>', INJECTION_SCRIPT + '</html>')
            else:
                content += INJECTION_SCRIPT
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(content.encode('utf-8'))))
            self.end_headers()
            try:
                self.wfile.write(content.encode('utf-8'))
            except (BrokenPipeError, ConnectionResetError):
                pass
                
        except Exception as e:
            print(f"[Error serving HTML] {e}")
            try:
                self.send_error(500, f"Internal Server Error: {e}")
            except (BrokenPipeError, ConnectionResetError):
                pass
    
    def find_html_file(self):
        """Find the HTML file to serve"""
        candidates = ['index_v0021.html', 'index_v0013.html', 'index.html', 'gallery.html']
        for candidate in candidates:
            if os.path.exists(candidate):
                return candidate
        
        for root, dirs, files in os.walk('.'):
            for candidate in candidates:
                if candidate in files:
                    return os.path.join(root, candidate)
        return None
    
    def serve_normal_file(self):
        """Serve normal files with error handling"""
        try:
            try:
                super().do_GET()
            except (BrokenPipeError, ConnectionResetError):
                pass
        except Exception as e:
            print(f"[Error serving {self.path}] {e}")
            try:
                self.send_error(404, "File not found")
            except (BrokenPipeError, ConnectionResetError):
                pass
    
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, HEAD, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

def flush_queue():
    """Background thread to flush queued events to database"""
    while True:
        time.sleep(3)
        if LoggingHandler._queue:
            with LoggingHandler._queue_lock:
                to_flush = LoggingHandler._queue.copy()
                LoggingHandler._queue.clear()
            
            if LoggingHandler.conn:
                success_count = 0
                for event in to_flush:
                    try:
                        cursor = LoggingHandler.conn.cursor()
                        cursor.execute('''
                            INSERT INTO page_events (timestamp, event_type, event_data, page_url, user_agent)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (
                            event['timestamp'],
                            event['type'],
                            json.dumps(event['data']),
                            event['url'],
                            event.get('user_agent', '')
                        ))
                        success_count += 1
                    except Exception as e:
                        print(f"[Queue Error] {e}")
                
                if success_count:
                    LoggingHandler.conn.commit()
                    print(f"[Queue] Flushed {success_count}/{len(to_flush)} events")

def find_available_port(start_port=8000, max_attempts=10):
    """Find an available port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socketserver.TCPServer(("", port), LoggingHandler) as test_server:
                test_server.server_close()
                return port
        except OSError:
            continue
    return None

def start_server(conn, port=8000):
    """Start the HTTP server with automatic port selection"""
    LoggingHandler.conn = conn
    
    # Find available port
    available_port = find_available_port(port)
    if not available_port:
        print("❌ No available ports found in range 8000-8010")
        return False
    
    if available_port != port:
        print(f"⚠️ Port {port} is busy, using port {available_port} instead")
    
    # Start queue flusher thread
    flusher = threading.Thread(target=flush_queue, daemon=True)
    flusher.start()
    
    try:
        with ThreadedTCPServer(("", available_port), LoggingHandler) as httpd:
            print(f"✓ Server running at http://localhost:{available_port}")
            print(f"✓ Logging database: {DB_PATH}")
            print("✓ Press Ctrl+C to stop")
            
            def signal_handler(sig, frame):
                print("\n🛑 Shutting down...")
                httpd.shutdown()
            
            signal.signal(signal.SIGTERM, signal_handler)
            
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\n🛑 Shutting down...")
                httpd.shutdown()
            
            # Final flush
            flush_queue()
            return True
            
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        return False

def main():
    print("=" * 60)
    print("LOGGING INJECTOR for Gallery (UPGRADED v2)")
    print("=" * 60)
    print()
    
    # Check for HTML files
    html_found = False
    for candidate in ['index_v0021.html', 'index_v0013.html', 'index.html']:
        if os.path.exists(candidate):
            html_found = True
            print(f"✓ Found {candidate}")
            break
    
    if not html_found:
        for root, dirs, files in os.walk('.'):
            if 'index_v0021.html' in files:
                html_found = True
                print(f"✓ Found index_v0021.html in {root}")
                os.chdir(root)
                break
            elif 'index_v0013.html' in files:
                html_found = True
                print(f"✓ Found index_v0013.html in {root}")
                os.chdir(root)
                break
    
    if not html_found:
        print("❌ ERROR: No HTML file found (index_v0021.html or index_v0013.html)!")
        print("   Please run: python3 build_final_gallery_v0021.py first")
        return
    
    # Initialize database
    try:
        conn = init_db()
        if not conn:
            print("❌ Failed to initialize database")
            return
    except Exception as e:
        print(f"❌ Database error: {e}")
        print("   Continuing with in-memory logging only...")
        conn = None
    
    # Add user_agent column if missing
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(page_events)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'user_agent' not in columns:
                cursor.execute("ALTER TABLE page_events ADD COLUMN user_agent TEXT")
                conn.commit()
                print("✓ Migrated database: added user_agent column")
        except Exception as e:
            print(f"⚠️ Migration warning: {e}")
    
    print()
    print("Starting server with logging...")
    print()
    
    # Open browser after delay
    port = 8000
    threading.Timer(2, lambda: webbrowser.open(f'http://localhost:{port}/index_v0021.html')).start()
    
    # Start server
    start_server(conn, port)

if __name__ == "__main__":
    main()