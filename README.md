# MacPushToAndroid

macOS 通知转发助手。当你在 Mac 上处于空闲状态时，自动将接收到的 macOS 系统通知转发到你的手机（通过 Telegram Bot 或电子邮件）。

## 功能特性

- **多通道转发**：支持通过 Telegram Bot 和 邮件 (SMTP SSL) 转发通知。
- **动态空闲检测**：通过读取系统休眠/输入空闲时间（`ioreg`），仅在用户离开 Mac（默认空闲 > 30秒）时进行转发，避免在活跃使用时产生重复骚扰。
- **系统通知解析**：以只读模式连接 macOS 系统的通知数据库（SQLite），并使用 `plistlib` 解析通知详细内容（标题、副标题、正文及来源 App）。
- **原生状态栏外壳**：包含用 Objective-C 编写的系统状态栏菜单外壳程序 (`MenuBarApp.m`)。
- **简易配置**：通过 JSON 配置文件动态调整，支持黑名单 App 过滤、转发通道切换、轮询间隔等。

## 项目结构

```text
├── forwarder.py                # 通知监听与转发核心守护进程 (Python)
├── MenuBarApp.m                # 原生 macOS 状态栏外壳 (Objective-C)
├── build_dist.sh               # 自动化编译与打包安装脚本
├── config.example.json         # 配置文件示例
├── com.a123.macpushtoandroid.plist # LaunchAgent 自动开机自启配置
└── web/                        # 配置界面的 Web 资源
```

## 安装与部署

### 1. 权限准备
由于 macOS 的安全机制，本程序运行需要连接系统的通知数据库，因此**运行本程序的终端（Terminal/iTerm/VSCode 等）或打包后的 App 必须获得「完全磁盘访问权限」 (Full Disk Access)**：
- 打开 `系统设置` -> `隐私与安全性` -> `完全磁盘访问权限`。
- 将您的终端或生成的 `MacPushToAndroid.app` 勾选启用。

### 2. 配置说明
配置文件存放在 `~/Library/Application Support/MacPushToAndroid/config.json` 中。
您可以参考项目中的 `config.example.json` 来创建它：

```json
{
  "enabled_channels": [
    "email",
    "telegram"
  ],
  "telegram_bot_token": "YOUR_BOT_TOKEN",
  "telegram_chat_id": "YOUR_CHAT_ID",
  "email_smtp_server": "smtp.qq.com",
  "email_smtp_port": 465,
  "email_sender": "your_email@qq.com",
  "email_password": "your_smtp_authorization_code",
  "email_receiver": "your_email@qq.com",
  "poll_interval_seconds": 2,
  "mute_when_active": true,
  "exclude_apps": [
    "com.apple.controlcenter",
    "com.apple.NotificationCenter",
    "com.apple.wifi"
  ]
}
```

### 3. 编译打包 (macOS)
通过运行自带的编译脚本，可自动将其打包为原生的 `.app` 应用程序并安装至 `/Applications`：
```bash
chmod +x build_dist.sh
./build_dist.sh
```

## 开机自启
如果需要作为开机自启服务在后台运行，可将 `com.a123.macpushtoandroid.plist` 放入 `~/Library/LaunchAgents/` 并加载它：
```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.a123.macpushtoandroid.plist
```

## 协议
[MIT License](LICENSE)
