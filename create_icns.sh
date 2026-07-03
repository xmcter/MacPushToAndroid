#!/bin/bash
set -e

SOURCE_PNG="app_icon_transparent.png"
ICONSET_DIR="app_icon.iconset"

echo "Creating iconset directory..."
mkdir -p "$ICONSET_DIR"

echo "Resizing images using sips..."
sips -s format png -z 16 16     "$SOURCE_PNG" --out "$ICONSET_DIR/icon_16x16.png"
sips -s format png -z 32 32     "$SOURCE_PNG" --out "$ICONSET_DIR/icon_16x16@2x.png"
sips -s format png -z 32 32     "$SOURCE_PNG" --out "$ICONSET_DIR/icon_32x32.png"
sips -s format png -z 64 64     "$SOURCE_PNG" --out "$ICONSET_DIR/icon_32x32@2x.png"
sips -s format png -z 128 128   "$SOURCE_PNG" --out "$ICONSET_DIR/icon_128x128.png"
sips -s format png -z 256 256   "$SOURCE_PNG" --out "$ICONSET_DIR/icon_128x128@2x.png"
sips -s format png -z 256 256   "$SOURCE_PNG" --out "$ICONSET_DIR/icon_256x256.png"
sips -s format png -z 512 512   "$SOURCE_PNG" --out "$ICONSET_DIR/icon_256x256@2x.png"
sips -s format png -z 512 512   "$SOURCE_PNG" --out "$ICONSET_DIR/icon_512x512.png"
sips -s format png -z 1024 1024 "$SOURCE_PNG" --out "$ICONSET_DIR/icon_512x512@2x.png"

echo "Converting iconset to icns..."
iconutil -c icns "$ICONSET_DIR"

echo "Cleaning up temporary files..."
rm -rf "$ICONSET_DIR"

echo "Successfully generated app_icon.icns!"
