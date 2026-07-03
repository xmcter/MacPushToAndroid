#import <Cocoa/Cocoa.h>
#import <WebKit/WebKit.h>

// Global dynamic paths
static NSString *kForwarderScript = nil;
static NSString *kConfigHelper = nil;
static NSString *kLogFile = nil;
static NSString *kPidFile = nil;
static NSString *kWebConfigScript = nil;

@interface AppDelegate : NSObject <NSApplicationDelegate, NSWindowDelegate>
@property (strong) NSStatusItem *statusItem;
@property (strong) NSTimer *refreshTimer;
@property (strong) NSWindow *configWindow;
@property (strong) WKWebView *webView;
@end

@implementation AppDelegate

- (void)applicationDidFinishLaunching:(NSNotification *)notification {
    // Resolve dynamic paths at runtime
    NSString *resourcePath = [[NSBundle mainBundle] resourcePath];
    kForwarderScript = [resourcePath stringByAppendingPathComponent:@"forwarder.py"];
    kConfigHelper = [resourcePath stringByAppendingPathComponent:@"config_helper.py"];
    kWebConfigScript = [resourcePath stringByAppendingPathComponent:@"web_config.py"];
    
    NSString *dataDir = [NSHomeDirectory() stringByAppendingPathComponent:@"Library/Application Support/MacPushToAndroid"];
    [[NSFileManager defaultManager] createDirectoryAtPath:dataDir withIntermediateDirectories:YES attributes:nil error:nil];
    kLogFile = [dataDir stringByAppendingPathComponent:@"forwarder.log"];
    kPidFile = [dataDir stringByAppendingPathComponent:@".daemon.pid"];

    // Create status bar item with variable length
    self.statusItem = [[NSStatusBar systemStatusBar] statusItemWithLength:NSVariableStatusItemLength];
    
    // Auto-start service if configuration is valid and not already running (default running state)
    if ([self configValid] && ![self daemonPID]) {
        [self startServiceSilently];
    }
    
    // Update menu immediately and then every 3 seconds
    [self refreshMenu];
    self.refreshTimer = [NSTimer scheduledTimerWithTimeInterval:3.0
                                                         target:self
                                                       selector:@selector(refreshMenu)
                                                       userInfo:nil
                                                        repeats:YES];
}

#pragma mark - Process Management

- (NSNumber *)daemonPID {
    NSString *pidStr = [NSString stringWithContentsOfFile:kPidFile
                                                 encoding:NSUTF8StringEncoding
                                                    error:nil];
    if (!pidStr) return nil;
    
    pid_t pid = (pid_t)[pidStr integerValue];
    if (pid <= 0) return nil;
    
    // Check if process is alive using kill -0
    if (kill(pid, 0) == 0) {
        return @(pid);
    }
    // Process is dead, clean up stale pid file
    [[NSFileManager defaultManager] removeItemAtPath:kPidFile error:nil];
    return nil;
}

- (NSString *)runShell:(NSString *)command {
    NSTask *task = [[NSTask alloc] init];
    task.launchPath = @"/bin/sh";
    task.arguments = @[@"-c", command];
    NSPipe *pipe = [NSPipe pipe];
    task.standardOutput = pipe;
    task.standardError = pipe;
    @try {
        [task launch];
        [task waitUntilExit];
    } @catch (NSException *e) {
        return @"";
    }
    NSData *data = [[pipe fileHandleForReading] readDataToEndOfFile];
    return [[NSString alloc] initWithData:data encoding:NSUTF8StringEncoding] ?: @"";
}

- (void)runShellAsync:(NSString *)command {
    NSTask *task = [[NSTask alloc] init];
    task.launchPath = @"/bin/sh";
    task.arguments = @[@"-c", command];
    // Explicitly decouple output descriptors to prevent subprocesses from locking standard streams
    task.standardOutput = [NSFileHandle fileHandleWithNullDevice];
    task.standardError = [NSFileHandle fileHandleWithNullDevice];
    @try {
        [task launch];
    } @catch (NSException *e) {
        NSLog(@"Error launching async command: %@", e);
    }
}

- (NSString *)configInfo {
    NSString *cmd = [NSString stringWithFormat:@"python3 '%@' get_info", kConfigHelper];
    return [self runShell:cmd];
}

- (BOOL)configValid {
    NSString *cmd = [NSString stringWithFormat:@"python3 '%@' check_config", kConfigHelper];
    NSString *result = [[self runShell:cmd] stringByTrimmingCharactersInSet:
                        [NSCharacterSet whitespaceAndNewlineCharacterSet]];
    return [result isEqualToString:@"true"];
}


#pragma mark - Menu Construction

- (void)refreshMenu {
    NSNumber *pid = [self daemonPID];
    BOOL running = (pid != nil);
    
    // Set native SF Symbols with template mode matching macOS dark/light menu bars
    NSImage *iconImage = nil;
    if (@available(macOS 11.0, *)) {
        iconImage = [NSImage imageWithSystemSymbolName:(running ? @"bell" : @"bell.slash")
                               accessibilityDescription:nil];
        if (iconImage) {
            [iconImage setTemplate:YES];
        }
    }
    
    if (iconImage) {
        self.statusItem.button.image = iconImage;
        self.statusItem.button.title = @"";
    } else {
        // Fallback to text emojis
        self.statusItem.button.image = nil;
        self.statusItem.button.title = running ? @"🔔" : @"🔕";
    }
    
    // Build menu
    NSMenu *menu = [[NSMenu alloc] init];
    
    // Toggle service switch with custom NSSwitch view
    NSView *customView = [[NSView alloc] initWithFrame:NSMakeRect(0, 0, 200, 30)];
    
    NSTextField *label = [[NSTextField alloc] initWithFrame:NSMakeRect(12, 5, 120, 20)];
    [label setStringValue:@"启用转发服务"];
    [label setBezeled:NO];
    [label setDrawsBackground:NO];
    [label setEditable:NO];
    [label setSelectable:NO];
    [label setFont:[NSFont systemFontOfSize:13]];
    [customView addSubview:label];
    
    NSSwitch *toggle = [[NSSwitch alloc] initWithFrame:NSMakeRect(140, 3, 50, 24)];
    [toggle setState:(running ? NSControlStateValueOn : NSControlStateValueOff)];
    [toggle setTarget:self];
    [toggle setAction:@selector(switchToggled:)];
    [customView addSubview:toggle];
    
    NSMenuItem *toggleItem = [[NSMenuItem alloc] init];
    [toggleItem setView:customView];
    [menu addItem:toggleItem];
    
    [menu addItem:[NSMenuItem separatorItem]];
    
    // Config info (read-only display)
    NSString *info = [self configInfo];
    NSArray *lines = [info componentsSeparatedByString:@"\n"];
    for (NSString *line in lines) {
        if (line.length == 0) continue;
        NSMenuItem *infoItem = [[NSMenuItem alloc] initWithTitle:line action:nil keyEquivalent:@""];
        infoItem.enabled = NO;
        [menu addItem:infoItem];
    }
    
    [menu addItem:[NSMenuItem separatorItem]];
    
    // Edit config (Dedicated window)
    NSMenuItem *editConfig = [[NSMenuItem alloc] initWithTitle:@"设置"
                                                        action:@selector(editConfig)
                                                 keyEquivalent:@","];
    editConfig.target = self;
    [menu addItem:editConfig];
    
    [menu addItem:[NSMenuItem separatorItem]];
    
    // Quit
    NSMenuItem *quit = [[NSMenuItem alloc] initWithTitle:@"退出"
                                                   action:@selector(quitApp)
                                            keyEquivalent:@"q"];
    quit.target = self;
    [menu addItem:quit];
    
    self.statusItem.menu = menu;
}

- (void)switchToggled:(NSSwitch *)sender {
    if (sender.state == NSControlStateValueOn) {
        [self startService];
    } else {
        [self stopService];
    }
}

#pragma mark - Actions

- (void)startServiceSilently {
    NSString *cmd = [NSString stringWithFormat:
                     @"python3 -u '%@' > '%@' 2>&1 & echo $! > '%@'",
                     kForwarderScript, kLogFile, kPidFile];
    [self runShell:cmd];
}

- (void)startService {
    if (![self configValid]) {
        NSAlert *alert = [[NSAlert alloc] init];
        alert.messageText = @"配置缺失";
        alert.informativeText = @"请先配置推送凭证（Bot Token / 邮箱 SMTP 参数）。";
        alert.alertStyle = NSAlertStyleWarning;
        [alert addButtonWithTitle:@"去配置"];
        [alert addButtonWithTitle:@"取消"];
        if ([alert runModal] == NSAlertFirstButtonReturn) {
            [self editConfig];
        }
        return;
    }
    
    [self startServiceSilently];
    
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(0.5 * NSEC_PER_SEC)),
                   dispatch_get_main_queue(), ^{
        [self refreshMenu];
        NSNumber *pid = [self daemonPID];
        if (pid) {
            [self sendNotification:@"通知转发器已启动"
                          subtitle:[NSString stringWithFormat:@"PID: %@", pid]];
        }
    });
}

- (void)stopService {
    NSNumber *pid = [self daemonPID];
    if (pid) {
        kill([pid intValue], SIGTERM);
        [[NSFileManager defaultManager] removeItemAtPath:kPidFile error:nil];
        [self sendNotification:@"通知转发器已停止" subtitle:@""];
    }
    // Fallback
    [self runShell:@"pkill -f 'forwarder.py'"];
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(0.5 * NSEC_PER_SEC)),
                   dispatch_get_main_queue(), ^{
        [self refreshMenu];
    });
}

- (void)editConfig {
    // Start local config web server asynchronously in background if it's dead, avoiding pipe inheritance deadlocks
    NSString *cmd = [NSString stringWithFormat:@"pgrep -f '[w]eb_config.py' || python3 '%@' >/dev/null 2>&1 &", kWebConfigScript];
    [self runShellAsync:cmd];
    
    // Create native Window in app controller if not yet built
    if (!self.configWindow) {
        NSRect rect = NSMakeRect(0, 0, 800, 620);
        NSUInteger style = NSWindowStyleMaskTitled | NSWindowStyleMaskClosable | NSWindowStyleMaskResizable;
        self.configWindow = [[NSWindow alloc] initWithContentRect:rect
                                                        styleMask:style
                                                          backing:NSBackingStoreBuffered
                                                            defer:NO];
        self.configWindow.title = @"MacPush 设置";
        self.configWindow.delegate = self;
        
        // Hide standard window buttons from zooming if desired, keep it simple
        [self.configWindow center];
        
        // Build WebKit WebView inside the native Window
        self.webView = [[WKWebView alloc] initWithFrame:self.configWindow.contentView.bounds];
        self.webView.autoresizingMask = NSViewWidthSizable | NSViewHeightSizable;
        [self.configWindow.contentView addSubview:self.webView];
    }
    
    // Load local REST settings URL
    NSURL *url = [NSURL URLWithString:@"http://127.0.0.1:18888"];
    NSURLRequest *req = [NSURLRequest requestWithURL:url];
    [self.webView loadRequest:req];
    
    // Direct focus and display window in foreground
    [self.configWindow makeKeyAndOrderFront:nil];
    [NSApp activateIgnoringOtherApps:YES];
}

- (void)viewLogs {
    // Create log file if it doesn't exist
    if (![[NSFileManager defaultManager] fileExistsAtPath:kLogFile]) {
        [[NSFileManager defaultManager] createFileAtPath:kLogFile contents:nil attributes:nil];
    }
    [[NSWorkspace sharedWorkspace] openFile:kLogFile withApplication:@"Console"];
}

- (void)quitApp {
    [NSApp terminate:nil];
}

- (void)sendNotification:(NSString *)title subtitle:(NSString *)subtitle {
    NSUserNotification *notif = [[NSUserNotification alloc] init];
    notif.title = @"MacPushToAndroid";
    notif.informativeText = title;
    notif.subtitle = subtitle;
    [[NSUserNotificationCenter defaultUserNotificationCenter] deliverNotification:notif];
}

#pragma mark - NSWindowDelegate

- (void)windowWillClose:(NSNotification *)notification {
    // Empty memory when closing
}

@end

// ============================================================
// Main entry point
// ============================================================
int main(int argc, const char *argv[]) {
    @autoreleasepool {
        NSApplication *app = [NSApplication sharedApplication];
        [app setActivationPolicy:NSApplicationActivationPolicyAccessory]; // Hide from Dock
        
        AppDelegate *delegate = [[AppDelegate alloc] init];
        app.delegate = delegate;
        
        [app run];
    }
    return 0;
}
