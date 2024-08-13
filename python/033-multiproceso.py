from tkinter import Tk, Canvas, Button, NW
from PIL import Image, ImageTk
import random
import os
import time
import noise
import math
import multiprocessing

# Create the render directory if it doesn't exist
output_dir = "render"
os.makedirs(output_dir, exist_ok=True)

# Function to interpolate between two colors
def interpolate_color(color1, color2, factor):
    return tuple(int(a + (b - a) * factor) for a, b in zip(color1, color2))

# Function to interpolate between two values
def interpolate_value(val1, val2, factor):
    return val1 + (val2 - val1) * factor

# Function to generate a section of the spherical terrain image in isometric perspective
def generate_section_isometric(params):
    x_start, x_end, y_start, y_end, width, height, scale, seed, water_level = params
    random.seed(seed)
    
    section = Image.new("RGB", (x_end - x_start, y_end - y_start))
    depth_section = Image.new("I", (x_end - x_start, y_end - y_start))  # 'I' mode for 16-bit grayscale (depth map)
    
    iso_width, iso_height = x_end - x_start, y_end - y_start
    center_x, center_y = iso_width // 2, iso_height // 2
    
    for x in range(x_start, x_end):
        for y in range(y_start, y_end):
            # Convert (x, y) to spherical coordinates
            lon = (x / width) * 2 * math.pi  # Longitude in [0, 2pi]
            lat = (y / height) * math.pi  # Latitude in [0, pi]
            lat = lat - math.pi / 2  # Adjust to range [-pi/2, pi/2]
            
            # Generate Perlin noise value for the spherical coordinates
            nx = math.cos(lat) * math.cos(lon)
            ny = math.cos(lat) * math.sin(lon)
            nz = math.sin(lat)
            perlin_value = noise.pnoise3(nx * scale, ny * scale, nz * scale, octaves=16, persistence=0.5, lacunarity=2.0)
            
            # Normalize the Perlin noise value to be between 0 and 1
            normalized_value = (perlin_value + 1) / 2
            
            # Interpolate thresholds based on latitude for gradual transition
            abs_lat = abs(lat)
            if abs_lat < math.pi / 4:
                coast_threshold = interpolate_value(0.45, 0.425, abs_lat / (math.pi / 4))
            else:
                coast_threshold = 0.425
            
            # Adjust thresholds based on water_level
            water_threshold = water_level
            coast_threshold = interpolate_value(water_threshold + 0.05, coast_threshold, abs_lat / (math.pi / 2))
            
            # Determine terrain type based on height and interpolate colors
            if normalized_value < water_threshold:
                color = interpolate_color((0, 0, 128), (200, 200, 255), normalized_value / water_threshold)  # Water
            elif normalized_value < coast_threshold:
                color = interpolate_color((250, 240, 190), (244, 164, 96), (normalized_value - water_threshold) / (coast_threshold - water_threshold))  # Coast
            elif normalized_value < 0.7:
                base_color = interpolate_color((244, 164, 96), (34, 139, 34), abs_lat / (math.pi / 2))  # Transition from warm to green
                color = interpolate_color(base_color, (107, 142, 35), (normalized_value - coast_threshold) / (0.7 - coast_threshold))  # Lowland
            else:
                base_color = interpolate_color((139, 137, 137), (34, 139, 34), abs_lat / (math.pi / 2))  # Transition from warm to green
                color = interpolate_color((200,200,200), (255, 255, 255), (normalized_value - 0.7) / (1.0 - 0.7))  # Mountain
            
            # Apply snow and ice cover to land areas (not to water)
            if normalized_value >= water_threshold:
                noise_factor = noise.pnoise3(x / 100.0, y / 100.0, seed)
                noise_factor = (noise_factor + 1) / 2  # Normalize noise to range [0, 1]
                if abs_lat > 2 * math.pi / 5:  # Ice caps near the poles
                    color = (255, 250, 250)  # Full ice cover
                elif abs_lat > math.pi / 4:  # Snow cover with noise
                    snow_factor = ((abs_lat - math.pi / 4) / (math.pi / 20)) * noise_factor
                    color = interpolate_color(color, (255, 255, 255), snow_factor)
            
            # Calculate isometric coordinates
            iso_x = int((x - x_start - (y - y_start)) * math.sqrt(3) / 2) + center_x
            iso_y = int((x - x_start + (y - y_start)) / 2 - normalized_value * 50) + center_y - (iso_height // 2)
            
            if 0 <= iso_x < iso_width and 0 <= iso_y < iso_height:
                section.putpixel((iso_x, iso_y), color)
                depth_section.putpixel((iso_x, iso_y), int(normalized_value * 65535))  # Depth as 16-bit grayscale intensity
    
    return section

# Set the dimensions for the equirectangular projection
multiplicador = 1024
multiplica = 32
width, height = multiplicador*multiplica*2, multiplicador*multiplica
scale = 5
water_level = 0.5  # Default water level, can be adjusted

# Initialize seed
seed = random.randint(0, 1000000)

# Define the section size for the 1% area
section_size = int(math.sqrt(0.0002 * width * height))

# Define the starting points for the 1% section at the center of the terrain
x_start = (width - section_size) // 2
y_start = (height - section_size) // 2

# Function to update the canvas with the new section
def update_canvas():
    global x_start, y_start, section_size, canvas, tk_img
    x_end = x_start + section_size
    y_end = y_start + section_size
    
    # Generate the section in isometric perspective using multiprocessing
    num_processes = multiprocessing.cpu_count()
    chunk_size = section_size // num_processes
    
    params = [
        (x_start + i * chunk_size, x_start + (i + 1) * chunk_size, y_start, y_end, width, height, scale, seed, water_level)
        for i in range(num_processes)
    ]
    
    with multiprocessing.Pool(num_processes) as pool:
        sections = pool.map(generate_section_isometric, params)
    
    combined_section = Image.new("RGB", (section_size, section_size))
    
    for i, section in enumerate(sections):
        combined_section.paste(section, (i * chunk_size, 0))
    
    # Convert the section to ImageTk format
    tk_img = ImageTk.PhotoImage(combined_section)
    
    # Update the canvas
    canvas.create_image(0, 0, anchor=NW, image=tk_img)

# Function to pan the view
def pan(dx, dy):
    global x_start, y_start, width, height, section_size
    x_start = (x_start + dx) % width
    y_start = (y_start + dy) % height
    update_canvas()

# Create the tkinter window
root = Tk()
root.title("Isometric Spherical Terrain Viewer")

# Create a canvas widget
canvas = Canvas(root, width=section_size, height=section_size)
canvas.pack()

# Create buttons to control panning
Button(root, text="Up", command=lambda: pan(0, -int(0.001 * height))).pack(side="top")
Button(root, text="Down", command=lambda: pan(0, int(0.001 * height))).pack(side="bottom")
Button(root, text="Left", command=lambda: pan(-int(0.001 * width), 0)).pack(side="left")
Button(root, text="Right", command=lambda: pan(int(0.001 * width), 0)).pack(side="right")

# Initialize the canvas with the first section
update_canvas()

# Start the tkinter main loop
root.mainloop()
