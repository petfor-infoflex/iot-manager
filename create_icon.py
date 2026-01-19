"""Generate application icon for IoT Device Manager."""

from PIL import Image, ImageDraw
import math

def create_icon():
    """Create a modern IoT/smart home icon."""
    # Create multiple sizes for ICO file
    sizes = [16, 32, 48, 64, 128, 256]
    images = []

    for size in sizes:
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Colors - modern blue gradient feel
        bg_color = (41, 128, 185)  # Nice blue
        accent_color = (52, 152, 219)  # Lighter blue
        white = (255, 255, 255)

        # Draw circular background
        padding = size // 16
        draw.ellipse(
            [padding, padding, size - padding, size - padding],
            fill=bg_color
        )

        # Draw house shape
        center_x = size // 2
        center_y = size // 2

        # House dimensions relative to size
        house_width = int(size * 0.45)
        house_height = int(size * 0.35)
        roof_height = int(size * 0.2)

        # House base position (slightly lower than center)
        house_top = center_y - int(size * 0.05)
        house_bottom = house_top + house_height
        house_left = center_x - house_width // 2
        house_right = center_x + house_width // 2

        # Draw roof (triangle)
        roof_points = [
            (center_x, house_top - roof_height),  # Top
            (house_left - size // 16, house_top),  # Bottom left
            (house_right + size // 16, house_top),  # Bottom right
        ]
        draw.polygon(roof_points, fill=white)

        # Draw house body
        draw.rectangle(
            [house_left, house_top, house_right, house_bottom],
            fill=white
        )

        # Draw door
        door_width = house_width // 3
        door_height = house_height // 2
        door_left = center_x - door_width // 2
        door_top = house_bottom - door_height
        draw.rectangle(
            [door_left, door_top, door_left + door_width, house_bottom],
            fill=bg_color
        )

        # Draw WiFi waves above house
        wave_center_x = center_x
        wave_center_y = house_top - roof_height - size // 10

        # Draw 2-3 arcs for WiFi symbol
        num_waves = 2 if size < 48 else 3
        for i in range(num_waves):
            arc_size = int(size * (0.08 + i * 0.06))
            if arc_size > 1:
                bbox = [
                    wave_center_x - arc_size,
                    wave_center_y - arc_size,
                    wave_center_x + arc_size,
                    wave_center_y + arc_size
                ]
                line_width = max(1, size // 24)
                draw.arc(bbox, 210, 330, fill=accent_color, width=line_width)

        # Small dot at wave center
        dot_size = max(1, size // 20)
        draw.ellipse(
            [wave_center_x - dot_size, wave_center_y - dot_size,
             wave_center_x + dot_size, wave_center_y + dot_size],
            fill=accent_color
        )

        images.append(img)

    # Save as ICO
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(script_dir, 'assets')
    os.makedirs(assets_dir, exist_ok=True)

    ico_path = os.path.join(assets_dir, 'icon.ico')
    png_path = os.path.join(assets_dir, 'icon.png')

    images[0].save(
        ico_path,
        format='ICO',
        sizes=[(s, s) for s in sizes],
        append_images=images[1:]
    )

    # Also save a PNG for other uses
    images[-1].save(png_path, format='PNG')

    print(f"Icon created: {ico_path} and {png_path}")

if __name__ == "__main__":
    create_icon()
