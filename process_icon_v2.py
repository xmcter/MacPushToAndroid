from PIL import Image, ImageDraw

def process_and_resize():
    src_path = "/Users/a123/.gemini/antigravity/brain/67cacd85-60da-4916-8e8c-b89fb6dea1ce/app_icon_source_1781335339929.png"
    dst_path = "/Users/a123/ProjectHub/Mine/Code/MacPushToAndroid/app_icon_transparent.png"
    
    img = Image.open(src_path).convert("RGBA")
    width, height = img.size
    
    # 1. Make the background transparent via flood fill from 4 corners
    transparent_color = (0, 0, 0, 0)
    corners = [(0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)]
    for corner in corners:
        ImageDraw.floodfill(img, corner, transparent_color, thresh=50)
        
    # 2. Find bounding box of the non-transparent content
    bbox = img.getbbox()
    if bbox:
        # Crop the content out
        cropped = img.crop(bbox)
        c_width = bbox[2] - bbox[0]
        c_height = bbox[3] - bbox[1]
        
        # 3. Calculate new size to fit standard macOS app icon grid (max 824x824 inside 1024x1024 canvas)
        max_target_dim = 824
        aspect_ratio = c_width / c_height
        
        if c_width > c_height:
            new_width = max_target_dim
            new_height = int(max_target_dim / aspect_ratio)
        else:
            new_height = max_target_dim
            new_width = int(max_target_dim * aspect_ratio)
            
        resized = cropped.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # 4. Center in a 1024x1024 canvas
        canvas = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
        offset_x = (1024 - new_width) // 2
        offset_y = (1024 - new_height) // 2
        canvas.paste(resized, (offset_x, offset_y))
        
        # Save output
        canvas.save(dst_path, "PNG")
        print(f"Successfully processed, centered and saved to {dst_path}")
    else:
        # Fallback if bbox is not found
        img.save(dst_path, "PNG")
        print(f"Fallback saved to {dst_path}")

if __name__ == "__main__":
    process_and_resize()
