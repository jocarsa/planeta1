from PIL import Image
import random
import os
import time
import noise

# Create the render directory if it doesn't exist
output_dir = "render"
os.makedirs(output_dir, exist_ok=True)

# Function to interpolate between two colors
def interpolate_color(color1, color2, factor):
    return tuple(int(a + (b - a) * factor) for a, b in zip(color1, color2))

# Function to generate a terrain image with height simulation and smooth gradients
def generate_terrain_image(width, height, scale=50):  # Increased scale factor to make noise patterns larger
    image = Image.new("RGB", (width, height))
    
    for x in range(width):
        for y in range(height):
            # Generate Perlin noise value for the pixel
            perlin_value = noise.pnoise2(x / scale, y / scale, octaves=6, persistence=0.5, lacunarity=2.0, repeatx=width, repeaty=height, base=0)
            
            # Normalize the Perlin noise value to be between 0 and 1
            normalized_value = (perlin_value + 1) / 2
            
            # Determine terrain type based on height and interpolate colors
            if normalized_value < 0.4:
                color = interpolate_color((0, 0, 128), (0, 0, 255), normalized_value / 0.4)  # Water
            elif normalized_value < 0.5:
                color = interpolate_color((244, 164, 96), (255, 250, 205), (normalized_value - 0.4) / 0.1)  # Coast
            elif normalized_value < 0.7:
                color = interpolate_color((34, 139, 34), (107, 142, 35), (normalized_value - 0.5) / 0.2)  # Lowland
            else:
                color = interpolate_color((139, 137, 137), (255, 255, 255), (normalized_value - 0.7) / 0.3)  # Mountain
            
            image.putpixel((x, y), color)
    
    return image

# Generate and save 10 images
for _ in range(10):
    # Generate random size maintaining 192x192 proportion
    base_width, base_height = 192, 192
    scale_factor = random.randint(1, 10)  # Random scale factor between 1 and 10
    width = base_width * scale_factor
    height = base_height * scale_factor
    
    # Generate the terrain image
    image = generate_terrain_image(width, height)

    # Scale the image to 8192x8192 without antialiasing
    scaled_image = image.resize((8192, 8192), Image.Resampling.NEAREST)

    # Save the scaled image with the current epoch time as the filename
    epoch_time = int(time.time())
    filename = os.path.join(output_dir, f"{epoch_time}.png")
    scaled_image.save(filename)

    # Wait a second to ensure unique filenames
    time.sleep(1)
