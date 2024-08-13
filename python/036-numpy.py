import numpy as np
from tkinter import Tk, Canvas, Button, NW
from PIL import Image, ImageTk
import random
import os
import noise
import math

# Create the render directory if it doesn't exist
output_dir = "render"
os.makedirs(output_dir, exist_ok=True)

# Function to interpolate between two colors
def interpolate_color(color1, color2, factor):
    factor = factor[:, :, None]  # Expand dimensions to match color arrays
    return np.uint8(color1 + (color2 - color1) * factor)

# Function to interpolate between two values
def interpolate_value(val1, val2, factor):
    return val1 + (val2 - val1) * factor

# Function to generate a section of the spherical terrain image in isometric perspective
def generate_section_isometric(x_start, x_end, y_start, y_end, width, height, scale, seed, water_level, height_multiplier):
    random.seed(seed)

    section = Image.new("RGB", (x_end - x_start, y_end - y_start))
    depth_section = Image.new("I", (x_end - x_start, y_end - y_start))  # 'I' mode for 16-bit grayscale (depth map)

    iso_width, iso_height = x_end - x_start, y_end - y_start
    center_x, center_y = iso_width // 2, iso_height // 2

    # Create arrays for x and y coordinates
    x_coords = np.arange(x_start, x_end)
    y_coords = np.arange(y_start, y_end)
    x_grid, y_grid = np.meshgrid(x_coords, y_coords)

    # Convert (x, y) to spherical coordinates
    lon = (x_grid / width) * 2 * np.pi  # Longitude in [0, 2pi]
    lat = (y_grid / height) * np.pi  # Latitude in [0, pi]
    lat = lat - np.pi / 2  # Adjust to range [-pi/2, pi/2]

    # Generate Perlin noise value for the spherical coordinates
    nx = np.cos(lat) * np.cos(lon)
    ny = np.cos(lat) * np.sin(lon)
    nz = np.sin(lat)
    perlin_values = np.vectorize(noise.pnoise3)(nx * scale, ny * scale, nz * scale, octaves=16, persistence=0.5, lacunarity=2.0)

    # Normalize the Perlin noise values to be between 0 and 1
    normalized_values = (perlin_values + 1) / 2

    # Interpolate thresholds based on latitude for gradual transition
    abs_lat = np.abs(lat)
    coast_threshold = np.where(abs_lat < np.pi / 4,
                               interpolate_value(0.45, 0.425, abs_lat / (np.pi / 4)),
                               0.425)

    # Adjust thresholds based on water_level
    water_threshold = water_level
    coast_threshold = interpolate_value(water_threshold + 0.05, coast_threshold, abs_lat / (np.pi / 2))

    # Determine terrain type based on height and interpolate colors
    colors = np.zeros((y_end - y_start, x_end - x_start, 3), dtype=np.uint8)
    below_water = normalized_values < water_threshold
    coast = (normalized_values >= water_threshold) & (normalized_values < coast_threshold)
    lowland = (normalized_values >= coast_threshold) & (normalized_values < 0.7)
    mountain = normalized_values >= 0.7

    colors[below_water] = interpolate_color(np.array([0, 0, 128]), np.array([200, 200, 255]), normalized_values[below_water].reshape(-1, 1) / water_threshold)
    colors[coast] = interpolate_color(np.array([250, 240, 190]), np.array([244, 164, 96]), (normalized_values[coast].reshape(-1, 1) - water_threshold) / (coast_threshold[coast].reshape(-1, 1) - water_threshold))

    base_color_lowland = interpolate_color(np.array([244, 164, 96]), np.array([34, 139, 34]), abs_lat[lowland].reshape(-1, 1) / (np.pi / 2))
    colors[lowland] = interpolate_color(base_color_lowland, np.array([107, 142, 35]), (normalized_values[lowland].reshape(-1, 1) - coast_threshold[lowland].reshape(-1, 1)) / (0.7 - coast_threshold[lowland].reshape(-1, 1)))

    base_color_mountain = interpolate_color(np.array([139, 137, 137]), np.array([34, 139, 34]), abs_lat[mountain].reshape(-1, 1) / (np.pi / 2))
    colors[mountain] = interpolate_color(np.array([200, 200, 200]), np.array([255, 255, 255]), (normalized_values[mountain].reshape(-1, 1) - 0.7) / (1.0 - 0.7))

    # Apply snow and ice cover to land areas (not to water)
    land = normalized_values >= water_threshold
    noise_factors = np.vectorize(noise.pnoise3)(x_grid / 100.0, y_grid / 100.0, seed)
    noise_factors = (noise_factors + 1) / 2  # Normalize noise to range [0, 1]

    ice_caps = abs_lat > 2 * np.pi / 5
    snow_cover = (abs_lat > np.pi / 4) & (abs_lat <= 2 * np.pi / 5)

    colors[land & ice_caps] = (255, 250, 250)  # Full ice cover
    snow_factors = ((abs_lat[snow_cover] - np.pi / 4) / (np.pi / 20)) * noise_factors[snow_cover]
    colors[snow_cover] = interpolate_color(colors[snow_cover], np.array([255, 255, 255]), snow_factors.reshape(-1, 1))

    # Calculate isometric coordinates
    iso_x = np.int32((x_grid - x_start - (y_grid - y_start)) * np.sqrt(3) / 2) + center_x
    iso_y = np.int32((x_grid - x_start + (y_grid - y_start)) / 2 - normalized_values * height_multiplier) + center_y - section_size + np.int32(height_multiplier * 1.7) // 2

    valid_x = (iso_x >= 0) & (iso_x < iso_width)
    valid_y = (iso_y >= 0) & (iso_y < iso_height)
    valid_coords = valid_x & valid_y

    for i in range(y_end - y_start):
        for j in range(x_end - x_start):
            if valid_coords[i, j]:
                section.putpixel((iso_x[i, j], iso_y[i, j]), tuple(colors[i, j]))
                depth_section.putpixel((iso_x[i, j], iso_y[i, j]), int(normalized_values[i, j] * 65535))  # Depth as 16-bit grayscale intensity

    return section

# Set the dimensions for the equirectangular projection
multiplicador = 1024
multiplica = 32
width, height = multiplicador * multiplica * 2, multiplicador * multiplica
scale = 5
water_level = 0.5  # Default water level, can be adjusted
height_multiplier = 1000  # Adjust this value to change the vertical scale in the isometric perspective

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
    
    # Generate the section in isometric perspective
    section = generate_section_isometric(x_start, x_end, y_start, y_end, width, height, scale, seed, water_level, height_multiplier)
    
    # Convert the section to ImageTk format
    tk_img = ImageTk.PhotoImage(section)
    
    # Calculate offsets to center the image on the canvas
    canvas_width = canvas.winfo_width()
    canvas_height = canvas.winfo_height()
    offset_x = (canvas_width - section_size) // 2
    offset_y = (canvas_height - section_size) // 2
    
    # Clear the canvas and update it with the new section
    canvas.delete("all")
    canvas.create_image(offset_x, offset_y, anchor=NW, image=tk_img)

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

# Initialize the canvas with the first section after the window is fully loaded
root.after(100, update_canvas)

# Start the tkinter main loop
root.mainloop()
