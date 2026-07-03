import os
import sys
import json
import socket
import plistlib
import subprocess
from http.server import SimpleHTTPRequestHandler, HTTPServer

# Import the existing forwarder notification functions for testing connectivity
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from forwarder import send_telegram_notification, send_email_notification

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# The web folder remains static inside App Resources bundle
WEB_DIR = os.path.join(BASE_DIR, "web")

# Config resides dynamically in Application Support
DATA_DIR = os.path.expanduser("~/Library/Application Support/MacPushToAndroid")
os.makedirs(DATA_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

class ConfigServerHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        # Override translate_path to serve static files from the 'web' folder
        clean_path = path.split('?')[0].split('#')[0]
        if clean_path == "/":
            clean_path = "/index.html"
        return os.path.join(WEB_DIR, clean_path.lstrip('/'))

    def do_GET(self):
        if self.path == "/api/config":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            
            config = {}
            if os.path.exists(CONFIG_FILE):
                try:
                    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                except Exception:
                    pass
            
            # Dynamically determine auto-start state based on LaunchAgent file presence
            agent_path = os.path.expanduser("~/Library/LaunchAgents/com.a123.macpushtoandroid.app.plist")
            config["auto_launch"] = os.path.exists(agent_path)
            
            self.wfile.write(json.dumps(config, ensure_ascii=False).encode('utf-8'))
        else:
            super().do_GET()

    def do_POST(self):
        # Allow reading empty body for /api/logs
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b'{}'
        
        try:
            req_data = json.loads(post_data.decode('utf-8')) if post_data != b'{}' else {}
        except Exception:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'Invalid JSON')
            return

        if self.path == "/api/config":
            try:
                auto_launch = req_data.get("auto_launch", False)
                agent_path = os.path.expanduser("~/Library/LaunchAgents/com.a123.macpushtoandroid.app.plist")
                
                if auto_launch:
                    os.makedirs(os.path.dirname(agent_path), exist_ok=True)
                    plist_content = {
                        "Label": "com.a123.macpushtoandroid.app",
                        "ProgramArguments": [ "/Applications/MacPushToAndroid.app/Contents/MacOS/MacPushToAndroid" ],
                        "RunAtLoad": True
                    }
                    with open(agent_path, 'wb') as fp:
                        plistlib.dump(plist_content, fp)
                else:
                    if os.path.exists(agent_path):
                        os.remove(agent_path)
                
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(req_data, f, indent=2, ensure_ascii=False)
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "message": str(e)}).encode('utf-8'))
                
        elif self.path == "/api/logs":
            try:
                log_file = os.path.join(DATA_DIR, "forwarder.log")
                if not os.path.exists(log_file):
                    with open(log_file, "w") as fp:
                        pass
                
                logs = ""
                try:
                    with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                        lines = f.readlines()
                        # Get last 1000 lines
                        logs = "".join(lines[-1000:])
                except Exception as e:
                    logs = f"Error reading logs: {e}"
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "logs": logs}, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "message": str(e)}).encode('utf-8'))
                
        elif self.path == "/api/test":
            channel = req_data.get("channel")
            success = False
            error_msg = ""
            
            test_app = "MacPush测试"
            test_title = "连接测试"
            test_subtitle = "这是一条来自配置中心的测试消息"
            test_body = "恭喜，你的推送渠道配置连接测试成功！"
            
            try:
                if channel == "telegram":
                    token = req_data.get("telegram_bot_token")
                    chat_id = req_data.get("telegram_chat_id")
                    success = send_telegram_notification(token, chat_id, test_app, test_title, test_subtitle, test_body)
                elif channel == "email":
                    server = req_data.get("email_smtp_server")
                    port = int(req_data.get("email_smtp_port", 465))
                    sender = req_data.get("email_sender")
                    password = req_data.get("email_password")
                    receiver = req_data.get("email_receiver")
                    success = send_email_notification(server, port, sender, password, receiver, test_app, test_title, test_subtitle, test_body)
                else:
                    error_msg = f"Unknown channel: {channel}"
            except Exception as e:
                error_msg = str(e)
                
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": success, "message": error_msg}).encode('utf-8'))

def get_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port

def main():
    port = 18888
    try:
        server = HTTPServer(('127.0.0.1', port), ConfigServerHandler)
    except OSError:
        port = get_free_port()
        server = HTTPServer(('127.0.0.1', port), ConfigServerHandler)
        
    url = f"http://127.0.0.1:{port}/"
    print(f"Config server listening silently on {url} ...")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping config server.")
        server.server_close()

if __name__ == "__main__":
    main()
