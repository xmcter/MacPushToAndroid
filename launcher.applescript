set python_script to "/Users/a123/ProjectHub/Mine/Code/MacPushToAndroid/forwarder.py"
set helper_script to "/Users/a123/ProjectHub/Mine/Code/MacPushToAndroid/config_helper.py"
set log_file to "/Users/a123/ProjectHub/Mine/Code/MacPushToAndroid/forwarder.log"
set pid_file to "/Users/a123/ProjectHub/Mine/Code/MacPushToAndroid/.daemon.pid"

repeat
	-- Get current status and settings
	try
		set current_info to do shell script "python3 " & quoted form of helper_script & " get_info"
	on error
		set current_info to "无法获取配置信息。"
	end try
	
	-- Check if daemon is running using pid file + kill -0
	set is_running to false
	set pid to ""
	try
		set pid to do shell script "cat " & quoted form of pid_file
		do shell script "kill -0 " & pid
		set is_running to true
	on error
		-- pid file doesn't exist or process is dead, clean up
		try
			do shell script "rm -f " & quoted form of pid_file
		end try
	end try
	
	if is_running then
		set status_text to "🟢 转发服务状态: 运行中 (PID: " & pid & ")"
	else
		set status_text to "🔴 转发服务状态: 未运行 (Stopped)"
	end if
	
	-- Build main menu items
	set menu_items to {}
	if is_running then
		set end of menu_items to "🔴 停止转发服务"
	else
		set end of menu_items to "🟢 启动转发服务"
	end if
	set end of menu_items to "⚙️ 修改配置参数"
	set end of menu_items to "📝 查看运行日志"
	set end of menu_items to "❌ 退出"
	
	set prompt_text to "--- 状态信息 ---" & linefeed & status_text & linefeed & linefeed & "--- 当前配置 ---" & linefeed & current_info & linefeed & linefeed & "请选择你要执行的操作："
	
	choose from list menu_items with title "MacPushToAndroid 控制中心" with prompt prompt_text default items {item 1 of menu_items} OK button name "确认" cancel button name "退出"
	
	set choice to result
	
	if choice is false then
		exit repeat
	else
		set selected_action to item 1 of choice
		
		if selected_action contains "启动转发服务" then
			-- Check if configuration is set
			set has_config to do shell script "python3 " & quoted form of helper_script & " check_config"
			if has_config is "false" then
				display dialog "检测到你尚未配置可用的推送参数！请先进行配置。" buttons {"好的"} default button "好的" with icon stop with title "MacPushToAndroid"
			else
				-- Start daemon and record PID
				do shell script "python3 " & quoted form of python_script & " > " & quoted form of log_file & " 2>&1 & echo $! > " & quoted form of pid_file
				delay 0.5
				-- Verify it started
				try
					set new_pid to do shell script "cat " & quoted form of pid_file
					do shell script "kill -0 " & new_pid
					display notification "通知转发器已在后台启动 (PID: " & new_pid & ")" with title "MacPushToAndroid"
				on error
					display dialog "启动失败！请检查 forwarder.log 日志文件。" buttons {"确定"} default button "确定" with icon stop with title "MacPushToAndroid"
				end try
			end if
			
		else if selected_action contains "停止转发服务" then
			try
				set stop_pid to do shell script "cat " & quoted form of pid_file
				do shell script "kill " & stop_pid
				do shell script "rm -f " & quoted form of pid_file
				display notification "通知转发器已停止运行" with title "MacPushToAndroid"
			on error
				-- Fallback: kill by pattern
				try
					do shell script "pkill -f 'forwarder.py'"
					do shell script "rm -f " & quoted form of pid_file
					display notification "通知转发器已停止运行" with title "MacPushToAndroid"
				end try
			end try
			
		else if selected_action contains "修改配置参数" then
			set channels to {"Telegram 机器人", "微信 (Server酱)", "微信 (WxPusher)"}
			choose from list channels with title "选择推送渠道" with prompt "请选择你偏好的推送接收渠道：" default items {"Telegram 机器人"} OK button name "下一步" cancel button name "取消"
			
			if result is not false then
				set chosen_channel to item 1 of result
				
				if chosen_channel is "Telegram 机器人" then
					display dialog "请输入 Telegram Bot Token:" default answer "" with title "Telegram 配置"
					set tg_token to text returned of result
					display dialog "请输入 Telegram Chat ID:" default answer "" with title "Telegram 配置"
					set tg_chat to text returned of result
					
					if tg_token is not "" and tg_chat is not "" then
						do shell script "python3 " & quoted form of helper_script & " set_telegram " & quoted form of tg_token & " " & quoted form of tg_chat
						display notification "Telegram 配置已保存" with title "MacPushToAndroid"
					end if
					
				else if chosen_channel is "微信 (Server酱)" then
					display dialog "请输入 Server酱 SendKey:" default answer "" with title "Server酱 配置"
					set sc_key to text returned of result
					
					if sc_key is not "" then
						do shell script "python3 " & quoted form of helper_script & " set_serverchan " & quoted form of sc_key
						display notification "Server酱 配置已保存" with title "MacPushToAndroid"
					end if
					
				else if chosen_channel is "微信 (WxPusher)" then
					display dialog "请输入 WxPusher AppToken:" default answer "" with title "WxPusher 配置"
					set wp_token to text returned of result
					display dialog "请输入 WxPusher UIDs (若有多个用户请用英文逗号分隔):" default answer "" with title "WxPusher 配置"
					set wp_uids to text returned of result
					
					if wp_token is not "" and wp_uids is not "" then
						do shell script "python3 " & quoted form of helper_script & " set_wxpusher " & quoted form of wp_token & " " & quoted form of wp_uids
						display notification "WxPusher 配置已保存" with title "MacPushToAndroid"
					end if
				end if
			end if
			
		else if selected_action contains "查看运行日志" then
			try
				do shell script "touch " & quoted form of log_file
				do shell script "open " & quoted form of log_file
			on error
				display dialog "无法打开日志文件！" buttons {"确定"} default button "确定" with title "MacPushToAndroid"
			end try
			
		else if selected_action contains "退出" then
			exit repeat
		end if
	end if
end repeat
