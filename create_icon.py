from PIL import Image, ImageDraw, ImageFont
import os

# Create icon sizes
sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]

images = []
for size in sizes:
    # Create new image with transparent background
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Calculate dimensions
    width, height = size
    margin = width // 8
    
    # Draw rounded rectangle background (green)
    draw.rounded_rectangle(
        [(margin, margin), (width - margin, height - margin)],
        radius=width // 8,
        fill=(16, 163, 127, 255)  # Green color #10a37f
    )
    
    # Try to draw "ez" text
    font_size = width // 3
    try:
        # Try to use a system font
        font = ImageFont.truetype("segoeui.ttf", font_size)
    except:
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            # Fallback to default font
            font = ImageFont.load_default()
    
    # Draw text "ez" in white
    text = "ez"
    
    # Get text bounding box
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Center text
    text_x = (width - text_width) // 2
    text_y = (height - text_height) // 2 - bbox[1]
    
    draw.text((text_x, text_y), text, fill=(255, 255, 255, 255), font=font)
    
    images.append(img)

# Save as ICO file
output_path = os.path.join(os.path.dirname(__file__), 'icon', 'ezText.ico')
os.makedirs(os.path.dirname(output_path), exist_ok=True)
images[0].save(output_path, format='ICO', sizes=[img.size for img in images])

print(f"Icon created: {output_path}")
