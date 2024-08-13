from PIL import Image
import random
import os
import time
from colorsys import hsv_to_rgb

# Create the render directory if it doesn't exist
output_dir = "render"
os.makedirs(output_dir, exist_ok=True)

# Function to generate a random color image with variations in value and saturation
def generate_color_variation_image():
    width, height = 192, 108
    image = Image.new("RGB", (width, height))

    # Select a random hue
    hue = random.random()

    for x in range(width):
        for y in range(height):
            # Randomize saturation and value
            saturation = random.uniform(0.5, 1.0)
            value = random.uniform(0.5, 1.0)

            # Convert HSV to RGB
            r, g, b = hsv_to_rgb(hue, saturation, value)
            r, g, b = int(r * 255), int(g * 255), int(b * 255)

            image.putpixel((x, y), (r, g, b))

    return image

# Generate and save 10 images
for _ in range(10):
    # Generate the image with color variations
    image = generate_color_variation_image()

    # Scale the image to 1920x1080 without antialiasing
    scaled_image = image.resize((1920, 1080), Image.Resampling.NEAREST)

    # Save the scaled image with the current epoch time as the filename
    epoch_time = int(time.time())
    filename = os.path.join(output_dir, f"{epoch_time}.png")
    scaled_image.save(filename)

    # Wait a second to ensure unique filenames
    time.sleep(1)
