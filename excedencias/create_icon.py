"""
Create Mexicana Logo Icon for Desktop Shortcut
"""
from PIL import Image, ImageDraw
from pathlib import Path


def create_mexicana_icon():
    """Create a simple Mexicana-inspired icon"""
    
    # Create 256x256 icon (Windows standard)
    size = 256
    img = Image.new('RGBA', (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    # Mexicana blue colors
    dark_blue = (13, 71, 161)  # #0D47A1
    light_blue = (33, 150, 243)  # #2196F3
    
    # Draw circular background
    margin = 10
    draw.ellipse(
        [margin, margin, size-margin, size-margin],
        fill=dark_blue,
        outline=light_blue,
        width=8
    )
    
    # Draw stylized "E" shape
    center_x = size // 2
    center_y = size // 2
    
    # E letter simplified
    bar_width = 15
    bar_length = 80
    
    # Vertical bar of E
    draw.rectangle(
        [
            center_x - 50, center_y - 60,
            center_x - 50 + bar_width, center_y + 60
        ],
        fill=light_blue
    )
    
    # Top horizontal bar
    draw.rectangle(
        [
            center_x - 50, center_y - 60,
            center_x - 50 + bar_length, center_y - 60 + bar_width
        ],
        fill=light_blue
    )
    
    # Middle horizontal bar
    draw.rectangle(
        [
            center_x - 50, center_y - 7,
            center_x - 50 + bar_length - 20, center_y + 7
        ],
        fill=light_blue
    )
    
    # Bottom horizontal bar
    draw.rectangle(
        [
            center_x - 50, center_y + 60 - bar_width,
            center_x - 50 + bar_length, center_y + 60
        ],
        fill=light_blue
    )
    
    # Add small aircraft silhouette
    aircraft_y = center_y + 40
    aircraft_x = center_x + 20
    
    # Simple aircraft shape
    draw.polygon([
        (aircraft_x, aircraft_y),
        (aircraft_x + 30, aircraft_y - 3),
        (aircraft_x + 35, aircraft_y - 3),
        (aircraft_x + 40, aircraft_y),
        (aircraft_x + 35, aircraft_y + 3),
        (aircraft_x + 30, aircraft_y + 3)
    ], fill=light_blue)
    
    # Wings
    draw.polygon([
        (aircraft_x + 15, aircraft_y - 8),
        (aircraft_x + 25, aircraft_y - 12),
        (aircraft_x + 30, aircraft_y - 8),
        (aircraft_x + 25, aircraft_y)
    ], fill=light_blue)
    
    draw.polygon([
        (aircraft_x + 15, aircraft_y + 8),
        (aircraft_x + 25, aircraft_y + 12),
        (aircraft_x + 30, aircraft_y + 8),
        (aircraft_x + 25, aircraft_y)
    ], fill=light_blue)
    
    # Save as ICO file
    output_dir = Path("assets/icons")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    ico_path = output_dir / "mexicana_app.ico"
    
    # Create multiple sizes for ICO format
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    images = []
    
    for size_tuple in sizes:
        resized = img.resize(size_tuple, Image.Resampling.LANCZOS)
        images.append(resized)
    
    # Save as ICO with multiple sizes
    images[0].save(
        ico_path,
        format='ICO',
        sizes=[(img.width, img.height) for img in images],
        append_images=images[1:]
    )
    
    # Also save as PNG for reference
    png_path = output_dir / "mexicana_app.png"
    img.save(png_path, 'PNG')
    
    print(f"✅ Icon created: {ico_path}")
    print(f"✅ PNG created: {png_path}")
    
    return ico_path


if __name__ == "__main__":
    create_mexicana_icon()

