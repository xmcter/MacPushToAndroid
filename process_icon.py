import os
from PIL import Image, ImageDraw

def process_icon():
    src_path = "/Users/a123/.gemini/antigravity/brain/67cacd85-60da-4916-8e8c-b89fb6dea1ce/app_icon_source_1781335339929.png"
    dst_path = "/Users/a123/ProjectHub/Mine/Code/MacPushToAndroid/app_icon_transparent.png"
    
    img = Image.open(src_path).convert("RGBA")
    width, height = img.size
    
    # We want to replace the light gray-white background with transparency.
    # The corner pixels are around (230, 230, 235).
    # We will use floodfill starting from all 4 corners.
    transparent_color = (0, 0, 0, 0)
    
    # Let's floodfill from the corners
    corners = [(0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)]
    for corner in corners:
        # We target the background color at that corner
        target_color = img.getpixel(corner)
        # Use a tolerance (thresh) to match similar colors in the gradient background
        ImageDraw.floodfill(img, corner, transparent_color, thresh=40)
        
    img.save(dst_path, "PNG")
    print(f"Processed image saved to {dst_path}")

if __name__ == "__main__":
    process_icon()
