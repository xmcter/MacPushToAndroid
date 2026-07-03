import sqlite3
import plistlib
import os
import time
import json
import urllib.request
import urllib.parse
import subprocess
import glob
import smtplib
from email.mime.text import MIMEText
from email.header import Header

# Store configuration and logs in the User Application Support folder instead of inside the App bundle
DATA_DIR = os.path.expanduser("~/Library/Application Support/MacPushToAndroid")
os.makedirs(DATA_DIR, exist_ok=True)

LAST_ID_FILE = os.path.join(DATA_DIR, ".last_id")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

def load_config():
    if not os.path.exists(CONFIG_FILE):
        print(f"Error: Configuration file not found at {CONFIG_FILE}")
        return None
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading config: {e}")
        return None

def find_db_path():
    # 1. Look in user temp directories (typical for newer macOS versions)
    try:
        darwin_user_dir = subprocess.check_output(["getconf", "DARWIN_USER_DIR"]).decode().strip()
        db_path = os.path.join(darwin_user_dir, "com.apple.notificationcenter", "db2", "db")
        if os.path.exists(db_path):
            return db_path
    except Exception:
        pass

    # 2. Look in Library Group Containers (alternative/older path)
    db_path = os.path.expanduser("~/Library/Group Containers/group.com.apple.usernoted/db2/db")
    if os.path.exists(db_path):
        return db_path

    # 3. Search using glob in case directories are nested differently
    if 'darwin_user_dir' in locals() and darwin_user_dir:
        search_pattern = os.path.join(darwin_user_dir, "**/com.apple.notificationcenter/**/db")
        found_files = glob.glob(search_pattern, recursive=True)
        if found_files:
            return found_files[0]

    return None

def get_app_name(bundle_id):
    if not bundle_id:
        return "Unknown App"
    
    # Common mappings for cleaner presentation
    mapping = {
        "com.tencent.xinWeChat": "WeChat",
        "com.apple.mobilesms": "iMessage",
        "com.apple.mail": "Mail",
        "com.apple.reminders": "Reminders",
        "com.apple.facetime": "FaceTime",
        "com.apple.ical": "Calendar",
        "com.google.chrome": "Chrome",
        "com.eg.android.AlipayGphone": "Alipay",
    }
    
    if bundle_id in mapping:
        return mapping[bundle_id]
        
    # Extract the last segment of the bundle ID as a fallback
    parts = bundle_id.split('.')
    if parts:
        name = parts[-1]
        if name.startswith("_system_center_:"):
            name = name.replace("_system_center_:", "")
        # Capitalize first letter
        return name.capitalize()
    return bundle_id

def send_telegram_notification(token, chat_id, app_name, title, subtitle, body):
    def escape_html(text):
        if not text:
            return ""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    app_name_esc = escape_html(app_name)
    title_esc = escape_html(title)
    subtitle_esc = escape_html(subtitle)
    body_esc = escape_html(body)

    message_lines = [f"<b>🔔 Mac 通知 ({app_name_esc})</b>"]
    if title_esc:
        message_lines.append(f"<b>标题:</b> {title_esc}")
    if subtitle_esc:
        message_lines.append(f"<b>副标题:</b> {subtitle_esc}")
    if body_esc:
        message_lines.append(f"<b>内容:</b> {body_esc}")
        
    message = "\n".join(message_lines)
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            res = json.loads(response.read().decode('utf-8'))
            return res.get("ok", False)
    except Exception as e:
        print(f"Telegram sending failed: {e}")
        return False

def send_email_notification(smtp_server, smtp_port, sender, password, receiver, app_name, title, subtitle, body):
    # Construct subject with actual app name, title, and notification content
    subject_parts = []
    if app_name:
        subject_parts.append(f"[{app_name}]")
    if title:
        subject_parts.append(title)
    if body:
        subject_parts.append(body)
        
    subject = " - ".join(subject_parts) if subject_parts else "新通知"
    # Limit length of email subject to keep it clean
    if len(subject) > 100:
        subject = subject[:97] + "..."
        
    content_lines = [f"应用: {app_name}"]
    if title:
        content_lines.append(f"标题: {title}")
    if subtitle:
        content_lines.append(f"副标题: {subtitle}")
    if body:
        content_lines.append(f"内容: {body}")
        
    from email.utils import formataddr
    content = "\n".join(content_lines)
    msg = MIMEText(content, 'plain', 'utf-8')
    msg['From'] = formataddr(('MacPush', sender))
    msg['To'] = formataddr(('', receiver))
    msg['Subject'] = Header(subject, 'utf-8')
    
    try:
        # Use SSL connection
        server = smtplib.SMTP_SSL(smtp_server, int(smtp_port), timeout=15)
        server.login(sender, password)
        server.sendmail(sender, [receiver], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Email sending failed: {e}")
        return False

def get_last_processed_id(cursor):
    if os.path.exists(LAST_ID_FILE):
        try:
            with open(LAST_ID_FILE, 'r') as f:
                return int(f.read().strip())
        except Exception as e:
            print(f"Error reading last ID file: {e}")

    try:
        cursor.execute("SELECT MAX(rec_id) FROM record")
        row = cursor.fetchone()
        if row and row[0] is not None:
            last_id = row[0]
            save_last_processed_id(last_id)
            print(f"Initialized last processed ID to latest DB record: {last_id}")
            return last_id
    except Exception as e:
        print(f"Error retrieving max rec_id from DB: {e}")
        
    return 0

def save_last_processed_id(rec_id):
    try:
        with open(LAST_ID_FILE, 'w') as f:
            f.write(str(rec_id))
    except Exception as e:
        print(f"Error saving last ID file: {e}")

def is_user_active(threshold_seconds=30):
    try:
        # Run ioreg to get HIDIdleTime in nanoseconds
        cmd = "ioreg -c IOHIDSystem | awk '/HIDIdleTime/ {print $NF; exit}'"
        output = subprocess.check_output(cmd, shell=True).decode().strip()
        if output:
            idle_ns = int(output)
            idle_secs = idle_ns / 1000000000.0
            return idle_secs < threshold_seconds
    except Exception as e:
        print(f"Error checking user idle time: {e}")
    return False

def main():
    print("Starting macOS Notification Forwarder...")
    
    db_path = find_db_path()
    if not db_path:
        print("Error: Could not find macOS notification database path.")
        return
    print(f"Using notification database: {db_path}")

    # Connect to SQLite in read-only mode to prevent write locking
    conn_uri = f"file:{db_path}?mode=ro"
    try:
        conn = sqlite3.connect(conn_uri, uri=True)
        cursor = conn.cursor()
    except sqlite3.OperationalError as e:
        print(f"Database connection error: {e}")
        print("Verify that this process/Terminal has 'Full Disk Access' permissions in System Settings.")
        return

    last_id = get_last_processed_id(cursor)
    print(f"Listening for new notifications (ID > {last_id})...")
    
    poll_interval = 2.0

    try:
        while True:
            # Reload config dynamically
            config = load_config() or {}
            enabled_channels = config.get("enabled_channels", [])
            if not enabled_channels:
                enabled_channels = [config.get("push_channel", "telegram")]
                
            poll_interval = config.get("poll_interval_seconds", 2.0)
            exclude_apps = config.get("exclude_apps", [])
            mute_when_active = config.get("mute_when_active", True)
            
            # Pre-validate enabled channels dynamically
            validated_channels = []
            for chan in enabled_channels:
                if chan == "telegram":
                    bot_token = config.get("telegram_bot_token")
                    chat_id = config.get("telegram_chat_id")
                    if bot_token and chat_id and bot_token != "YOUR_BOT_TOKEN" and chat_id != "YOUR_CHAT_ID":
                        validated_channels.append(("telegram", (bot_token, chat_id)))
                elif chan == "email":
                    server = config.get("email_smtp_server")
                    port = config.get("email_smtp_port", 465)
                    sender = config.get("email_sender")
                    password = config.get("email_password")
                    receiver = config.get("email_receiver")
                    if server and sender and password and receiver and "YOUR_" not in sender and "YOUR_" not in password:
                        validated_channels.append(("email", (server, port, sender, password, receiver)))

            try:
                conn.rollback()  # Reset transaction to see newly committed records in WAL mode
                cursor.execute("""
                    SELECT r.rec_id, a.identifier, r.data 
                    FROM record r
                    JOIN app a ON r.app_id = a.app_id
                    WHERE r.rec_id > ?
                    ORDER BY r.rec_id ASC
                """, (last_id,))
                
                rows = cursor.fetchall()
            except sqlite3.OperationalError as e:
                print(f"Database read query failed: {e}. Retrying soon...")
                time.sleep(poll_interval)
                continue

            for row in rows:
                rec_id, app_identifier, blob_data = row
                
                last_id = rec_id
                save_last_processed_id(last_id)

                if app_identifier in exclude_apps:
                    continue
                
                title = ""
                subtitle = ""
                body = ""
                
                if blob_data:
                    try:
                        data_dict = plistlib.loads(blob_data)
                        req_dict = data_dict.get('req', {})
                        title = req_dict.get('titl', '')
                        subtitle = req_dict.get('subt', '')
                        body = req_dict.get('body', '')
                    except Exception as e:
                        print(f"Failed to parse plist for record {rec_id}: {e}")
                        continue
                
                app_name = get_app_name(app_identifier)
                
                # Check if user is active on Mac (no need to forward duplicate notifications)
                if mute_when_active and is_user_active(30):
                    print(f"User is active on Mac. Skipping forwarding for notification: [{app_name}] {title}")
                    continue
                
                print(f"New notification: [{app_name}] {title} - {body}")
                
                # Forward notification to all validated channels
                for chan_type, args in validated_channels:
                    success = False
                    if chan_type == "telegram":
                        success = send_telegram_notification(args[0], args[1], app_name, title, subtitle, body)
                    elif chan_type == "email":
                        success = send_email_notification(args[0], args[1], args[2], args[3], args[4], app_name, title, subtitle, body)
                    
                    if not success:
                        print(f"Warning: Failed to forward notification {rec_id} via {chan_type}.")
            
            time.sleep(poll_interval)
            
    except KeyboardInterrupt:
        print("\nStopping macOS Notification Forwarder daemon.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
