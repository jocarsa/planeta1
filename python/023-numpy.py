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

# Function to generate a section of the spherical terrain image using NumPy for faster calculations
def generate_section(args):
    x_start, x_end, width, height, scale, seed, water_level = args
    random.seed(seed)
    
    section = np.zeros((x_end - x_start, height, 3), dtype=np.uint8)
    depth_section = np.zeros((x_end - x_start, height), dtype=np.uint16)
    
    x_coords = np.arange(x_start, x_end)
    y_coords = np.arange(height)
    
    lon = (x_coords[:, None] / width) * 2 * np.pi  # Longitude in [0, 2pi]
    lat = (y_coords[None, :] / height) * np.pi - np.pi / 2  # Latitude in [-pi/2, pi/2]
    
    nx = np.cos(lat) * np.cos(lon)
    ny = np.cos(lat) * np.sin(lon)
    nz = np.sin(lat)
    
    perlin_values = np.vectorize(noise.pnoise3)(
        nx * scale, ny * scale, nz * scale,
        octaves=16, persistence=0.5, lacunarity=2.0,
        repeatx=width, repeaty=height, base=seed
    )
    
    normalized_values = (perlin_values + 1) / 2
    
    abs_lat = np.abs(lat)
    coast_threshold = np.where(
        abs_lat < np.pi / 4,
        interpolate_value(0.45, 0.425, abs_lat / (np.pi / 4)),
        0.425
    )
    
    coast_threshold = interpolate_value(water_level + 0.05, coast_threshold, abs_lat / (np.pi / 2))
    
    water_mask = normalized_values < water_level
    coast_mask = (normalized_values >= water_level) & (normalized_values < coast_threshold)
    lowland_mask = (normalized_values >= coast_threshold) & (normalized_values < 0.7)
    mountain_mask = normalized_values >= 0.7
    
    section[water_mask] = interpolate_color((0, 0, 128), (0, 0, 255), normalized_values[water_mask] / water_level)
    section[coast_mask] = interpolate_color((250, 240, 190), (244, 164, 96), (normalized_values[coast_mask] - water_level) / (coast_threshold[coast_mask] - water_level))
    
    base_color_lowland = interpolate_color((244, 164, 96), (34, 139, 34), abs_lat[lowland_mask] / (np.pi / 2))
    section[lowland_mask] = interpolate_color(base_color_lowland, (107, 142, 35), (normalized_values[lowland_mask] - coast_threshold[lowland_mask]) / (0.7 - coast_threshold[lowland_mask]))
    
    base_color_mountain = interpolate_color((139, 137, 137), (34, 139, 34), abs_lat[mountain_mask] / (np.pi / 2))
    section[mountain_mask] = interpolate_color(base_color_mountain, (255, 255, 255), (normalized_values[mountain_mask] - 0.7) / (1.0 - 0.7))
    
    ice_caps_mask = abs_lat > 2 * np.pi / 5
    snow_cover_mask = (abs_lat > np.pi / 4) & ~ice_caps_mask
    
    section[ice_caps_mask] = (255, 250, 250)
    
    noise_factor = np.vectorize(noise.pnoise3)(x_coords[:, None] / 100.0, y_coords[None, :] / 100.0, seed)
    noise_factor = (noise_factor + 1) / 2
    
    snow_factor = ((abs_lat - np.pi / 4) / (np.pi / 20)) * noise_factor
    snow_cover_color = interpolate_color(section[snow_cover_mask], (255, 255, 255), snow_factor[snow_cover_mask])
    section[snow_cover_mask] = snow_cover_color
    
    depth_section = (normalized_values * 65535).astype(np.uint16)
    
    section_image = Image.fromarray(section)
    depth_image = Image.fromarray(depth_section, mode='I')
    
    return section_image, depth_image

def combine_sections(sections, width, height):
    combined = Image.new("RGB", (width, height))
    depth_combined = Image.new("I", (width, height))  # 'I' mode for 16-bit grayscale
    
    for section, depth_section, x_start in sections:
        combined.paste(section, (x_start, 0))
        depth_combined.paste(depth_section, (x_start, 0))
    
    return combined, depth_combined

def main():
    # Set the dimensions for the equirectangular projection
    width, height = 8192, 4096
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
