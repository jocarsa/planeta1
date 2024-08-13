from PIL import Image
import random
import os
import time
import noise
from colorsys import hsv_to_rgb

# Create the render directory if it doesn't exist
output_dir = "render"
os.makedirs(output_dir, exist_ok=True)

# Function to generate a Perlin noise image with variations in value and saturation
def generate_perlin_noise_image(hue, width=192, height=108, scale=10):
    image = Image.new("RGB", (width, height))
    
    for x in range(width):
        for y in range(height):
            # Generate Perlin noise value for the pixel
            perlin_value = noise.pnoise2(x / scale, y / scale, octaves=6, persistence=0.5, lacunarity=2.0, repeatx=width, repeaty=height, base=0)
            
            # Normalize the Perlin noise value to be between 0 and 1
            normalized_value = (perlin_value + 1) / 2
            
            # Set saturation and value based on the noise value
            saturation = 0.5 + 0.5 * normalized_value
            value = 0.5 + 0.5 * normalized_value
            
            # Convert HSV to RGB
            r, g, b = hsv_to_rgb(hue, saturation, value)
            r, g, b = int(r * 255), int(g * 255), int(b * 255)
            
            image.putpixel((x, y), (r, g, b))
    
    return image

# Generate and save 10 images
for _ in range(10):
    # Select a random hue
    hue = random.random()
    
    # Generate the Perlin noise image with the selected hue
    image = generate_perlin_noise_image(hue)

    # Scale the image to 1920x1080 without antialiasing
    scaled_image = image.resize((1920, 1080), Image.Resampling.NEAREST)

    # Save the scaled image with the current epoch time as the filename
    epoch_time = int(time.time())
    filename = os.path.join(output_dir, f"{epoch_time}.png")
    scaled_image.save(filename)

    # Wait a second to ensure unique filenames
    time.sleep(1)
