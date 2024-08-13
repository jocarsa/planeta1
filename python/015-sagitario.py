from PIL import Image
import random
import os
import time
import noise
import math

# Create the render directory if it doesn't exist
output_dir = "render"
os.makedirs(output_dir, exist_ok=True)

# Function to interpolate between two colors
def interpolate_color(color1, color2, factor):
    return tuple(int(a + (b - a) * factor) for a, b in zip(color1, color2))

# Function to generate spherical terrain images with height simulation and smooth gradients
def generate_spherical_terrain_images(width, height, scale=1, seed=None):
    if seed is not None:
        random.seed(seed)
        noise.seed(seed)
        
    diffuse_image = Image.new("RGB", (width, height))
    depth_image = Image.new("L", (width, height))  # 'L' mode for grayscale (depth map)
    
    for x in range(width):
        for y in range(height):
            # Convert (x, y) to spherical coordinates
            lon = (x / width) * 2 * math.pi  # Longitude in [0, 2pi]
            lat = (y / height) * math.pi  # Latitude in [0, pi]
            lat = lat - math.pi / 2  # Adjust to range [-pi/2, pi/2]
            
            # Generate Perlin noise value for the spherical coordinates
            nx = math.cos(lat) * math.cos(lon)
            ny = math.cos(lat) * math.sin(lon)
            nz = math.sin(lat)
            perlin_value = noise.pnoise3(nx * scale, ny * scale, nz * scale, octaves=6, persistence=0.5, lacunarity=2.0)
            
            # Normalize the Perlin noise value to be between 0 and 1
            normalized_value = (perlin_value + 1) / 2
            
            # Determine terrain type based on height and interpolate colors
            if normalized_value < 0.4:
                color = interpolate_color((0, 0, 128), (0, 0, 255), normalized_value / 0.4)  # Water
            elif normalized_value < 0.5:
                color = interpolate_color((244, 164, 96), (255, 250, 205), (normalized_value - 0.4) / 0.1)  # Coast
            elif normalized_value < 0.7:
                base_color = interpolate_color((244, 164, 96), (34, 139, 34), abs(lat) / (math.pi / 2))  # Transition from warm to green
                color = interpolate_color(base_color, (107, 142, 35), (normalized_value - 0.5) / 0.2)  # Lowland
            else:
                base_color = interpolate_color((139, 137, 137), (34, 139, 34), abs(lat) / (math.pi / 2))  # Transition from warm to green
                color = interpolate_color(base_color, (255, 255, 255), (normalized_value - 0.7) / 0.3)  # Mountain
            
            # Apply snow and ice cover to land areas (not to water)
            if normalized_value >= 0.4:
                if abs(lat) > 2 * math.pi / 5:  # Ice caps near the poles
                    color = (255, 250, 250)  # Full ice cover
                elif abs(lat) > math.pi / 4:  # Snow cover
                    snow_factor = (abs(lat) - math.pi / 4) / (math.pi / 20)
                    color = interpolate_color(color, (255, 255, 255), snow_factor)
            
            diffuse_image.putpixel((x, y), color)
            depth_image.putpixel((x, y), int(normalized_value * 255))  # Depth as grayscale intensity
    
    return diffuse_image, depth_image

# Generate and save 10 images
for i in range(10):
    # Set the dimensions for the equirectangular projection
    width, height = 8192, 4096
    
    # Use a different seed for each iteration
    seed = random.randint(0, 1000000)
    
    # Generate the spherical terrain images
    diffuse_image, depth_image = generate_spherical_terrain_images(width, height, seed=seed)

    # Save the images with the current epoch time as the filename
    epoch_time = int(time.time())
    diffuse_filename = os.path.join(output_dir, f"{epoch_time}_diffuse.png")
    depth_filename = os.path.join(output_dir, f"{epoch_time}_depth.png")
    diffuse_image.save(diffuse_filename)
    depth_image.save(depth_filename)

    # Wait a second to ensure unique filenames
    time.sleep(1)
