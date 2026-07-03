import json
import os
import sys

# Store configuration and logs in the User Application Support folder instead of inside the App bundle
DATA_DIR = os.path.expanduser("~/Library/Application Support/MacPushToAndroid")
os.makedirs(DATA_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

def load_config():
    if not os.path.exists(CONFIG_FILE):
        # Create a default configuration structure
        default_config = {
            "enabled_channels": ["telegram"],
            "push_channel": "telegram",
            "telegram_bot_token": "YOUR_BOT_TOKEN",
            "telegram_chat_id": "YOUR_CHAT_ID",
            "email_smtp_server": "smtp.qq.com",
            "email_smtp_port": 465,
            "email_sender": "YOUR_SENDER_EMAIL@qq.com",
            "email_password": "YOUR_SMTP_AUTHORIZATION_CODE",
            "email_receiver": "YOUR_RECEIVER_EMAIL@qq.com",
            "poll_interval_seconds": 2.0,
            "exclude_apps": [
                "com.apple.controlcenter",
                "com.apple.NotificationCenter",
                "com.apple.wifi"
            ]
        }
        save_config(default_config)
        return default_config
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            # Ensure enabled_channels exists
            if "enabled_channels" not in config:
                config["enabled_channels"] = [config.get("push_channel", "telegram")]
            return config
    except Exception:
        return {}

def save_config(config):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving config: {e}", file=sys.stderr)

def get_info():
    config = load_config()
    enabled_channels = config.get("enabled_channels", [])
    if not enabled_channels:
        enabled_channels = [config.get("push_channel", "telegram")]
    
    names = []
    for c in enabled_channels:
        if c == "telegram":
            names.append("Telegram")
        elif c == "email":
            names.append("邮箱")
            
    info_lines = [f"● 启用的渠道: {', '.join(names)}"]
    info_lines.append(f"● 轮询速度: {config.get('poll_interval_seconds', 2.0)} 秒")
    return "\n".join(info_lines)

def check_config():
    config = load_config()
    enabled_channels = config.get("enabled_channels", [])
    if not enabled_channels:
        enabled_channels = [config.get("push_channel", "telegram")]
        
    if not enabled_channels:
        return "false"
        
    for channel in enabled_channels:
        if channel == "telegram":
            token = config.get("telegram_bot_token", "")
            chat_id = config.get("telegram_chat_id", "")
            if not token or not chat_id or "YOUR_" in token or "YOUR_" in chat_id:
                return "false"
        elif channel == "email":
            server = config.get("email_smtp_server", "")
            sender = config.get("email_sender", "")
            password = config.get("email_password", "")
            receiver = config.get("email_receiver", "")
            if not server or not sender or not password or not receiver or "YOUR_" in sender or "YOUR_" in password:
                return "false"
            
    return "true"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)
        
    cmd = sys.argv[1]
    if cmd == "get_info":
        print(get_info())
    elif cmd == "check_config":
        print(check_config())
