import numpy as np
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

# Function to interpolate between two values
def interpolate_value(val1, val2, factor):
    return val1 + (val2 - val1) * factor

# Function to generate a section of the spherical terrain image
def generate_section(args):
    x_start, x_end, width, height, scale, seed, water_level = args
    random.seed(seed)
    
    section = np.zeros((x_end - x_start, height, 3), dtype=np.uint8)
    depth_section = np.zeros((x_end - x_start, height), dtype=np.uint16)
    
    x = np.arange(x_start, x_end)
    y = np.arange(height)
    xv, yv = np.meshgrid(x, y, indexing='ij')
    
    lon = (xv / width) * 2 * np.pi
    lat = (yv / height) * np.pi - np.pi / 2
    
    nx = np.cos(lat) * np.cos(lon)
    ny = np.cos(lat) * np.sin(lon)
    nz = np.sin(lat)
    
    perlin_values = np.vectorize(noise.pnoise3)(nx * scale, ny * scale, nz * scale, octaves=16, persistence=0.5, lacunarity=2.0)
    normalized_values = (perlin_values + 1) / 2
    
    abs_lat = np.abs(lat)
    coast_threshold = np.where(abs_lat < np.pi / 4, interpolate_value(0.45, 0.425, abs_lat / (np.pi / 4)), 0.425)
    coast_threshold = interpolate_value(water_level + 0.05, coast_threshold, abs_lat / (np.pi / 2))
    
    # Determine terrain type based on height and interpolate colors
    water_mask = normalized_values < water_level
    coast_mask = (normalized_values >= water_level) & (normalized_values < coast_threshold)
    lowland_mask = (normalized_values >= coast_threshold) & (normalized_values < 0.7)
    mountain_mask = normalized_values >= 0.7
    
    water_color = np.array([0, 0, 128]) * (1 - normalized_values / water_level)[:, :, None] + np.array([0, 0, 255]) * (normalized_values / water_level)[:, :, None]
    coast_color = np.array([250, 240, 190]) * (1 - (normalized_values - water_level) / (coast_threshold - water_level))[:, :, None] + np.array([244, 164, 96]) * ((normalized_values - water_level) / (coast_threshold - water_level))[:, :, None]
    base_color_lowland = np.array([244, 164, 96]) * (1 - abs_lat / (np.pi / 2))[:, :, None] + np.array([34, 139, 34]) * (abs_lat / (np.pi / 2))[:, :, None]
    lowland_color = base_color_lowland * (1 - (normalized_values - coast_threshold) / (0.7 - coast_threshold))[:, :, None] + np.array([107, 142, 35]) * ((normalized_values - coast_threshold) / (0.7 - coast_threshold))[:, :, None]
    base_color_mountain = np.array([139, 137, 137]) * (1 - abs_lat / (np.pi / 2))[:, :, None] + np.array([34, 139, 34]) * (abs_lat / (np.pi / 2))[:, :, None]
    mountain_color = base_color_mountain * (1 - (normalized_values - 0.7) / (1.0 - 0.7))[:, :, None] + np.array([255, 255, 255]) * ((normalized_values - 0.7) / (1.0 - 0.7))[:, :, None]
    
    section[water_mask] = water_color[water_mask]
    section[coast_mask] = coast_color[coast_mask]
    section[lowland_mask] = lowland_color[lowland_mask]
    section[mountain_mask] = mountain_color[mountain_mask]
    
    # Apply snow and ice cover to land areas (not to water)
    noise_factor = np.vectorize(noise.pnoise3)(xv / 100.0, yv / 100.0, seed)
    noise_factor = (noise_factor + 1) / 2
    
    ice_cap_mask = abs_lat > 2 * np.pi / 5
    snow_cover_mask = (abs_lat > np.pi / 4) & ~ice_cap_mask
    snow_factor = ((abs_lat - np.pi / 4) / (np.pi / 20)) * noise_factor
    
    section[snow_cover_mask] = interpolate_color(section[snow_cover_mask], (255, 255, 255), snow_factor[snow_cover_mask])
    section[ice_cap_mask] = (255, 250, 250)
    
    depth_section = (normalized_values * 65535).astype(np.uint16)
    
    return Image.fromarray(section), Image.fromarray(depth_section)

def combine_sections(sections, width, height):
    combined = Image.new("RGB", (width, height))
    depth_combined = Image.new("I", (width, height))  # 'I' mode for 16-bit grayscale
    
    for section, depth_section, x_start in sections:
        combined.paste(section, (x_start, 0))
        depth_combined.paste(depth_section, (x_start, 0))
    
    return combined, depth_combined

def main():
    # Set the dimensions for the equirectangular projection
    width, height = 1024, 512
    scale = 5
    water_level = 0.5  # Default water level, can be adjusted
    
    # Use a different seed for each iteration
    seed = random.randint(0, 1000000)
    epoch_time = int(time.time())
    
    # Define the sections for parallel processing
    num_sections = cpu_count()
    section_width = width // num_sections
    tasks = [(i * section_width, (i + 1) * section_width if i < num_sections - 1 else width, width, height, scale, seed, water_level) for i in range(num_sections)]
    
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
    depth_combined.save(depth_filename, format="PNG", bitdepth=16)

if __name__ == "__main__":
    main()
