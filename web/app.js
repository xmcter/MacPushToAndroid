document.addEventListener('DOMContentLoaded', () => {
    loadSettings();
    setupToggleListeners();
});

// Show dynamic notification toasts
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    let icon = 'ℹ️';
    if (type === 'success') icon = '✅';
    if (type === 'error') icon = '❌';
    
    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s cubic-bezier(0.16, 1, 0.3, 1) reverse';
        toast.addEventListener('animationend', () => toast.remove());
    }, 4000);
}

// Add state update visual styling when toggle switches change
function setupToggleListeners() {
    ['telegram', 'email'].forEach(channel => {
        const toggle = document.getElementById(`toggle-${channel}`);
        const card = document.getElementById(`card-${channel}`);
        
        toggle.addEventListener('change', () => {
            if (toggle.checked) {
                card.classList.add('active');
            } else {
                card.classList.remove('active');
            }
        });
    });
}

// Tab Switching
function switchTab(tabId) {
    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
    document.getElementById(`nav-btn-${tabId}`).classList.add('active');
    
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
    document.getElementById(`tab-${tabId}`).classList.add('active');
    
    if (tabId === 'logs') {
        loadLogs();
    }
}

// Fetch and display log file content natively
async function loadLogs() {
    const logText = document.getElementById('log-text');
    logText.textContent = '正在加载运行日志...';
    try {
        const response = await fetch('/api/logs', { method: 'POST' });
        if (!response.ok) throw new Error('加载日志失败');
        const res = await response.json();
        if (res.success) {
            logText.textContent = res.logs || '(目前没有记录到任何运行日志)';
            setTimeout(() => {
                logText.scrollTop = logText.scrollHeight;
            }, 50);
        } else {
            throw new Error(res.message || '未知错误');
        }
    } catch (err) {
        logText.textContent = `加载日志失败: ${err.message}`;
        showToast(err.message, 'error');
    }
}

// Fetch configuration from API
async function loadSettings() {
    try {
        const response = await fetch('/api/config');
        if (!response.ok) throw new Error('读取配置失败');
        
        const config = await response.json();
        
        // Setup channels status
        const enabled = config.enabled_channels || [config.push_channel || 'telegram'];
        ['telegram', 'email'].forEach(channel => {
            const toggle = document.getElementById(`toggle-${channel}`);
            const card = document.getElementById(`card-${channel}`);
            const isEnabled = enabled.includes(channel);
            
            toggle.checked = isEnabled;
            if (isEnabled) {
                card.classList.add('active');
            } else {
                card.classList.remove('active');
            }
        });
        
        // Load credentials fields
        document.getElementById('tg-token').value = config.telegram_bot_token || '';
        document.getElementById('tg-chatid').value = config.telegram_chat_id || '';
        
        // Email SMTP fields
        document.getElementById('email-server').value = config.email_smtp_server || 'smtp.qq.com';
        document.getElementById('email-port').value = config.email_smtp_port || 465;
        document.getElementById('email-sender').value = config.email_sender || '';
        document.getElementById('email-password').value = config.email_password || '';
        document.getElementById('email-receiver').value = config.email_receiver || '';
        
        // Globals
        document.getElementById('toggle-autolaunch').checked = config.auto_launch || false;
        document.getElementById('toggle-mute-active').checked = config.hasOwnProperty('mute_when_active') ? config.mute_when_active : true;
        document.getElementById('poll-interval').value = config.poll_interval_seconds || 2.0;
        document.getElementById('exclude-apps').value = (config.exclude_apps || []).join('\n');
        
        showToast('配置加载成功', 'success');
    } catch (err) {
        showToast(`加载配置失败: ${err.message}`, 'error');
    }
}

// Save all configurations
async function saveSettings() {
    const enabled_channels = [];
    if (document.getElementById('toggle-telegram').checked) enabled_channels.push('telegram');
    if (document.getElementById('toggle-email').checked) enabled_channels.push('email');
    
    if (enabled_channels.length === 0) {
        showToast('请至少启用一个推送渠道！', 'error');
        return;
    }
    
    const excludeInput = document.getElementById('exclude-apps').value;
    const exclude_apps = excludeInput.split('\n').map(x => x.trim()).filter(x => x.length > 0);
    
    const payload = {
        enabled_channels,
        push_channel: enabled_channels[0], // backward compatibility
        telegram_bot_token: document.getElementById('tg-token').value.trim(),
        telegram_chat_id: document.getElementById('tg-chatid').value.trim(),
        email_smtp_server: document.getElementById('email-server').value.trim(),
        email_smtp_port: parseInt(document.getElementById('email-port').value) || 465,
        email_sender: document.getElementById('email-sender').value.trim(),
        email_password: document.getElementById('email-password').value.trim(),
        email_receiver: document.getElementById('email-receiver').value.trim(),
        auto_launch: document.getElementById('toggle-autolaunch').checked,
        mute_when_active: document.getElementById('toggle-mute-active').checked,
        poll_interval_seconds: parseFloat(document.getElementById('poll-interval').value) || 2.0,
        exclude_apps
    };
    
    try {
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) throw new Error('保存请求被拒绝');
        const res = await response.json();
        if (res.success) {
            showToast('配置已成功保存！', 'success');
        } else {
            throw new Error(res.message || '未知错误');
        }
    } catch (err) {
        showToast(`保存失败: ${err.message}`, 'error');
    }
}

// Trigger single channel connectivity test
async function testChannel(channel) {
    let payload = {};
    if (channel === 'telegram') {
        payload = {
            channel,
            telegram_bot_token: document.getElementById('tg-token').value.trim(),
            telegram_chat_id: document.getElementById('tg-chatid').value.trim()
        };
    } else if (channel === 'email') {
        payload = {
            channel,
            email_smtp_server: document.getElementById('email-server').value.trim(),
            email_smtp_port: parseInt(document.getElementById('email-port').value) || 465,
            email_sender: document.getElementById('email-sender').value.trim(),
            email_password: document.getElementById('email-password').value.trim(),
            email_receiver: document.getElementById('email-receiver').value.trim()
        };
    }
    
    showToast(`正在发送 ${channel.toUpperCase()} 测试消息...`, 'info');
    
    try {
        const response = await fetch('/api/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const res = await response.json();
        if (res.success) {
            showToast(`${channel.toUpperCase()} 测试成功，请检查接收端！`, 'success');
        } else {
            throw new Error(res.message || '发送失败');
        }
    } catch (err) {
        showToast(`测试失败: ${err.message}`, 'error');
    }
}
