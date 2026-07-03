#!/bin/bash
set -e

echo "=== Starting MacPushToAndroid App Build ==="

# Clean old builds
rm -rf MacPushToAndroid.app
rm -f MenuBarApp

# Compile the native Objective-C app with WebKit linked
echo "Compiling Objective-C wrapper..."
clang -framework Cocoa -framework Foundation -framework WebKit -o MenuBarApp MenuBarApp.m -fobjc-arc

# Create the standard App bundle directory structure
echo "Creating app directory structure..."
mkdir -p MacPushToAndroid.app/Contents/MacOS
mkdir -p MacPushToAndroid.app/Contents/Resources/web

# Move the executable
mv MenuBarApp MacPushToAndroid.app/Contents/MacOS/MacPushToAndroid

# Copy Python scripts to the bundle Resources directory
echo "Packing python helper daemons..."
cp forwarder.py MacPushToAndroid.app/Contents/Resources/
cp config_helper.py MacPushToAndroid.app/Contents/Resources/
cp web_config.py MacPushToAndroid.app/Contents/Resources/

# Copy the web assets to the bundle Resources web directory
echo "Packing Web UI assets..."
cp web/index.html MacPushToAndroid.app/Contents/Resources/web/
cp web/style.css MacPushToAndroid.app/Contents/Resources/web/
cp web/app.js MacPushToAndroid.app/Contents/Resources/web/

# Copy the app icon to the bundle Resources directory
if [ -f "app_icon.icns" ]; then
    echo "Packing App Icon..."
    cp app_icon.icns MacPushToAndroid.app/Contents/Resources/
fi

# Write the Info.plist
echo "Writing Info.plist..."
cat > MacPushToAndroid.app/Contents/Info.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>MacPushToAndroid</string>
    <key>CFBundleIdentifier</key>
    <string>com.a123.macpushtoandroid</string>
    <key>CFBundleName</key>
    <string>MacPushToAndroid</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundleIconFile</key>
    <string>app_icon.icns</string>
    <key>LSUIElement</key>
    <true/>
</dict>
</plist>
EOF

# Copy the newly built standalone bundle to /Applications
echo "Installing to /Applications..."
rm -rf /Applications/MacPushToAndroid.app
cp -R MacPushToAndroid.app /Applications/

echo "=== Build completed successfully! ==="
echo "The standalone application is now located at: /Applications/MacPushToAndroid.app"
echo "You can share this .app bundle with other users."
