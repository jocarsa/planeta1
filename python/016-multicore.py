from PIL import Image
import random
import os
import time
import noise
import math
from multiprocessing import Pool, cpu_count

# Create the render directory if it doesn't exist
output_dir = "render"
os.makedirs(output_dir, exist_ok=True)

# Function to interpolate between two colors
def interpolate_color(color1, color2, factor):
    return tuple(int(a + (b - a) * factor) for a, b in zip(color1, color2))

# Function to generate a section of the spherical terrain image
def generate_section(args):
    x_start, x_end, width, height, scale, seed = args
    random.seed(seed)
    
    section = Image.new("RGB", (x_end - x_start, height))
    depth_section = Image.new("L", (x_end - x_start, height))  # 'L' mode for grayscale (depth map)
    
    for x in range(x_start, x_end):
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
            
            section.putpixel((x - x_start, y), color)
            depth_section.putpixel((x - x_start, y), int(normalized_value * 255))  # Depth as grayscale intensity
    
    return section, depth_section

def combine_sections(sections, width, height):
    combined = Image.new("RGB", (width, height))
    depth_combined = Image.new("L", (width, height))
    
    for section, depth_section, x_start in sections:
        combined.paste(section, (x_start, 0))
        depth_combined.paste(depth_section, (x_start, 0))
    
    return combined, depth_combined

def main():
    # Set the dimensions for the equirectangular projection
    width, height = 8192, 4096
    scale = 1
    
    # Use a different seed for each iteration
    seed = random.randint(0, 1000000)
    epoch_time = int(time.time())
    
    # Define the sections for parallel processing
    num_sections = cpu_count()
    section_width = width // num_sections
    tasks = [(i * section_width, (i + 1) * section_width if i < num_sections - 1 else width, width, height, scale, seed) for i in range(num_sections)]
    
    # Use multiprocessing to generate image sections in parallel
    pool = Pool(processes=num_sections)
    results = pool.map(generate_section, tasks)
    
    # Combine sections into a single image
    sections = [(result[0], result[1], i * section_width) for i, result in enumerate(results)]
    combined, depth_combined = combine_sections(sections, width, height)
    
    # Save the combined images
    diffuse_filename = os.path.join(output_dir, f"{epoch_time}_diffuse.png")
    depth_filename = os.path.join(output_dir, f"{epoch_time}_depth.png")
    combined.save(diffuse_filename)
    depth_combined.save(depth_filename)

if __name__ == "__main__":
    main()
