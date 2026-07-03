from PIL import Image, ImageDraw

def process_with_mask():
    src_path = "/Users/a123/.gemini/antigravity/brain/67cacd85-60da-4916-8e8c-b89fb6dea1ce/app_icon_source_1781335339929.png"
    dst_path = "/Users/a123/ProjectHub/Mine/Code/MacPushToAndroid/app_icon_transparent.png"
    
    img = Image.open(src_path).convert("RGBA")
    
    # Crop exactly to the blue squircle box: (205, 206, 818, 819)
    # This box was determined by scanning for the dark blue squircle base.
    cropped = img.crop((205, 206, 818, 819))
    
    # Create a mathematically perfect macOS squircle mask
    # macOS standard corner radius is approx 22.5% of the side length.
    # 613 * 0.225 = 138 pixels.
    mask = Image.new("L", (613, 613), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([0, 0, 612, 612], radius=138, fill=255)
    
    # Apply the mask to the cropped image
    clean_icon = Image.new("RGBA", (613, 613), (0, 0, 0, 0))
    clean_icon.paste(cropped, (0, 0), mask=mask)
    
    # Scale to macOS standard grid size (824x824)
    target_dim = 824
    resized = clean_icon.resize((target_dim, target_dim), Image.Resampling.LANCZOS)
    
    # Center in a 1024x1024 transparent canvas
    canvas = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    offset = (1024 - target_dim) // 2
    canvas.paste(resized, (offset, offset))
    
    # Save output
    canvas.save(dst_path, "PNG")
    print(f"Icon processed with mathematical squircle mask and saved to {dst_path}")

if __name__ == "__main__":
    process_with_mask()
