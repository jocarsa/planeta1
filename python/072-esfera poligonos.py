import sqlite3
import numpy as np
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from PIL import Image, ImageTk, ImageDraw
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

# Function to interpolate between two values
def interpolate_value(val1, val2, factor):
    return val1 + (val2 - val1) * factor

# Function to generate a section of the spherical terrain image in isometric perspective
def generate_section_isometric(x_start, x_end, y_start, y_end, width, height, scale, seed, water_level, height_multiplier, cur, y_pixel_offset, pixel_separation):
    random.seed(seed)
    
    iso_width, iso_height = (x_end - x_start) * pixel_separation, (y_end - y_start) * pixel_separation
    section = Image.new("RGB", (iso_width, iso_height))
    draw = ImageDraw.Draw(section)
    
    center_x, center_y = iso_width // 2, iso_height // 2
    
    # Batch fetch data from database
    cur.execute("SELECT x, y, color, height FROM terrain WHERE x BETWEEN ? AND ? AND y BETWEEN ? AND ?",
                (x_start, x_end - 1, y_start, y_end - 1))
    data = cur.fetchall()
    
    # Convert data to a dictionary for quick access
    terrain_dict = {(x, y): (color_str, height) for x, y, color_str, height in data}
    
    # First pass: draw the terrain
    for x in range(x_start, x_end):
        for y in range(y_start, y_end):
            if (x, y) not in terrain_dict:
                continue
            
            color_str, height = terrain_dict[(x, y)]
            color = tuple(map(int, color_str.split(',')))
            normalized_value = height / 65535.0
            
            # Calculate isometric coordinates for current point and its neighbors
            iso_x = int(((x - x_start - (y - y_start)) * math.sqrt(3) / 2) * pixel_separation) + center_x
            iso_y = int(((x - x_start + (y - y_start)) / 2 - normalized_value * height_multiplier) * pixel_separation) + center_y - int(height_multiplier * pixel_separation * 0.65) + y_pixel_offset
            
            neighbors = [
                (x + 1, y), (x, y + 1), (x + 1, y + 1)
            ]
            
            neighbor_iso = []
            for nx, ny in neighbors:
                if (nx, ny) in terrain_dict:
                    n_color_str, n_height = terrain_dict[(nx, ny)]
                    n_normalized_value = n_height / 65535.0
                    n_iso_x = int(((nx - x_start - (ny - y_start)) * math.sqrt(3) / 2) * pixel_separation) + center_x
                    n_iso_y = int(((nx - x_start + (ny - y_start)) / 2 - n_normalized_value * height_multiplier) * pixel_separation) + center_y - int(height_multiplier * pixel_separation * 0.65) + y_pixel_offset
                    neighbor_iso.append((n_iso_x, n_iso_y, n_normalized_value))
                else:
                    neighbor_iso = []
                    break
            
            if len(neighbor_iso) == 3:
                # Draw the isometric tile as a filled polygon with height-adjusted vertices
                points = [
                    (iso_x, iso_y),  # Current point
                    (neighbor_iso[0][0], neighbor_iso[0][1]),  # Right neighbor
                    (neighbor_iso[2][0], neighbor_iso[2][1]),  # Bottom-right neighbor
                    (neighbor_iso[1][0], neighbor_iso[1][1])   # Bottom neighbor
                ]
                draw.polygon(points, fill=color)
                draw.line([points[0], points[1]], fill="black")
                draw.line([points[1], points[2]], fill="black")
                draw.line([points[2], points[3]], fill="black")
                draw.line([points[3], points[0]], fill="black")
            else:
                # Draw the isometric tile aligned with the xy-plane
                points = [
                    (iso_x, iso_y),  # Top
                    (iso_x + pixel_separation * math.sqrt(3) / 2, iso_y + pixel_separation / 2),  # Right
                    (iso_x, iso_y + pixel_separation),  # Bottom
                    (iso_x - pixel_separation * math.sqrt(3) / 2, iso_y + pixel_separation / 2)  # Left
                ]
                draw.polygon(points, fill=color)
                draw.line([points[0], points[1]], fill="black")
                draw.line([points[1], points[2]], fill="black")
                draw.line([points[2], points[3]], fill="black")
                draw.line([points[3], points[0]], fill="black")
    
    # Second pass: draw the water surface
    water_surface = Image.new("RGBA", (iso_width, iso_height), (0, 0, 0, 0))
    draw_water = ImageDraw.Draw(water_surface)
    
    for x in range(x_start, x_end):
        for y in range(y_start, y_end):
            if (x, y) not in terrain_dict:
                continue

            color_str, height = terrain_dict[(x, y)]
            normalized_value = height / 65535.0

            if normalized_value < water_level:
                iso_x = int(((x - x_start - (y - y_start)) * math.sqrt(3) / 2) * pixel_separation) + center_x
                iso_y = int(((x - x_start + (y - y_start)) / 2 - water_level * height_multiplier) * pixel_separation) + center_y - int(height_multiplier * pixel_separation * 0.65) + y_pixel_offset
                
                neighbors = [
                    (x + 1, y), (x, y + 1), (x + 1, y + 1)
                ]
                
                neighbor_iso = []
                for nx, ny in neighbors:
                    if (nx, ny) in terrain_dict:
                        n_color_str, n_height = terrain_dict[(nx, ny)]
                        n_normalized_value = n_height / 65535.0
                        n_iso_x = int(((nx - x_start - (ny - y_start)) * math.sqrt(3) / 2) * pixel_separation) + center_x
                        n_iso_y = int(((nx - x_start + (ny - y_start)) / 2 - water_level * height_multiplier) * pixel_separation) + center_y - int(height_multiplier * pixel_separation * 0.65) + y_pixel_offset
                        neighbor_iso.append((n_iso_x, n_iso_y, n_normalized_value))
                    else:
                        neighbor_iso = []
                        break
                
                if len(neighbor_iso) == 3:
                    water_points = [
                        (iso_x, iso_y),  # Current point
                        (neighbor_iso[0][0], neighbor_iso[0][1]),  # Right neighbor
                        (neighbor_iso[2][0], neighbor_iso[2][1]),  # Bottom-right neighbor
                        (neighbor_iso[1][0], neighbor_iso[1][1])   # Bottom neighbor
                    ]
                    draw_water.polygon(water_points, fill=(0, 0, 255, 128))  # Blue transparent color
    
    # Combine the terrain and water surface
    section = Image.alpha_composite(section.convert("RGBA"), water_surface)

    return section.convert("RGB")

# Set the dimensions for the equirectangular projection
multiplicador = 1024
multiplica = 8
width, height = multiplicador * multiplica * 2, multiplicador * multiplica
scale = 5
water_level = 0.5  # Default water level, can be adjusted

# Initialize seed
seed = random.randint(0, 1000000)

# Define the section size for the larger canvas
section_size = int(math.sqrt(0.00001 * width * height)) * 2  # Increase the section size by a factor of 2

# Define the starting points for the section at the center of the terrain
x_start = (width - section_size) // 2
y_start = (height - section_size) // 2

# Function to update the canvas with the new section
def update_canvas():
    global x_start, y_start, section_size, canvas, tk_img, cur, height_multiplier, y_pixel_offset, pixel_separation
    x_end = x_start + section_size
    y_end = y_start + section_size
    
    # Generate the section in isometric perspective
    section = generate_section_isometric(x_start, x_end, y_start, y_end, width, height, scale, seed, water_level, height_multiplier, cur, y_pixel_offset, pixel_separation)
    
    # Convert the section to ImageTk format
    tk_img = ImageTk.PhotoImage(section)
    
    # Calculate offsets to center the image on the canvas
    canvas_width = canvas.winfo_width()
    canvas_height = canvas.winfo_height()
    offset_x = (canvas_width - section.width) // 2
    offset_y = (canvas_height - section.height) // 2
    
    # Clear the canvas and update it with the new section
    canvas.delete("all")
    canvas.create_image(offset_x, offset_y, anchor=NW, image=tk_img)

def draw_sphere():
    global cur, sphere_canvas
    
    # Define sphere parameters
    radius = 200
    center_x = radius + 50  # Adjusted to ensure the sphere is centered
    center_y = radius + 50  # Adjusted to ensure the sphere is centered
    num_meridians = 64
    num_parallels = 32
    
    sphere_canvas.delete("all")
    
    def get_screen_coordinates(lat, lon):
        x = radius * math.cos(lat) * math.cos(lon)
        y = radius * math.cos(lat) * math.sin(lon)
        z = radius * math.sin(lat)
        screen_x = center_x + x / (1 + z / (2 * radius))
        screen_y = center_y - y / (1 + z / (2 * radius))
        return screen_x, screen_y

    def get_color(lat, lon):
        terrain_x = int((lon / (2 * math.pi)) * width)
        terrain_y = int((lat + math.pi / 2) / math.pi * height)
        cur.execute("SELECT color FROM terrain WHERE x = ? AND y = ?", (terrain_x, terrain_y))
        result = cur.fetchone()
        if result:
            color_str = result[0]
            color = "#" + "".join(f"{int(c):02x}" for c in map(int, color_str.split(',')))
            return color
        return "#000000"  # Default to black if no color is found
    
    for i in range(num_parallels):
        lat1 = (i / num_parallels) * math.pi - math.pi / 2
        lat2 = ((i + 1) / num_parallels) * math.pi - math.pi / 2
        for j in range(num_meridians):
            lon1 = (j / num_meridians) * 2 * math.pi
            lon2 = ((j + 1) / num_meridians) * 2 * math.pi
            
            x1, y1 = get_screen_coordinates(lat1, lon1)
            x2, y2 = get_screen_coordinates(lat1, lon2)
            x3, y3 = get_screen_coordinates(lat2, lon2)
            x4, y4 = get_screen_coordinates(lat2, lon1)
            
            color1 = get_color(lat1, lon1)
            color2 = get_color(lat1, lon2)
            color3 = get_color(lat2, lon2)
            color4 = get_color(lat2, lon1)
            
            # Average color for the face (simple approach)
            avg_color = "#{:02x}{:02x}{:02x}".format(
                (int(color1[1:3], 16) + int(color2[1:3], 16) + int(color3[1:3], 16) + int(color4[1:3], 16)) // 4,
                (int(color1[3:5], 16) + int(color2[3:5], 16) + int(color3[3:5], 16) + int(color4[3:5], 16)) // 4,
                (int(color1[5:7], 16) + int(color2[5:7], 16) + int(color3[5:7], 16) + int(color4[5:7], 16)) // 4
            )
            
            # Draw the face as a polygon
            sphere_canvas.create_polygon(
                x1, y1, x2, y2, x3, y3, x4, y4,
                fill=avg_color, outline="black"
            )
                
    # Draw sphere outline
    sphere_canvas.create_oval(center_x - radius, center_y - radius, center_x + radius, center_y + radius, outline="white")

# Function to pan the view
def pan(dx, dy):
    global x_start, y_start, width, height, section_size
    x_start = (x_start + dx) % width
    y_start = (y_start + dy) % height
    update_canvas()

# Function to initialize the database
def init_db():
    conn = sqlite3.connect("terrain_data.db")
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS terrain (x INTEGER, y INTEGER, color TEXT, height INTEGER, PRIMARY KEY (x, y))")
    return conn, cur

# Function to update height multiplier
def update_height_multiplier(val):
    global height_multiplier
    height_multiplier = int(float(val))
    update_canvas()

# Function to update y pixel offset
def update_y_pixel_offset(val):
    global y_pixel_offset
    y_pixel_offset = int(float(val))
    update_canvas()

# Function to update pixel separation
def update_pixel_separation(val):
    global pixel_separation
    pixel_separation = int(float(val))
    canvas.config(width=section_size * pixel_separation, height=section_size * pixel_separation)
    update_canvas()

# Initialize database
conn, cur = init_db()

# Pre-calculate the terrain data if not already done
if cur.execute("SELECT COUNT(*) FROM terrain").fetchone()[0] == 0:
    print("Calculating terrain data. This may take a while...")
    for x in range(width):
        for y in range(height):
            # Generate Perlin noise value for the spherical coordinates
            lon = (x / width) * 2 * math.pi  # Longitude in [0, 2pi]
            lat = (y / height) * math.pi  # Latitude in [0, pi]
            lat = lat - math.pi / 2  # Adjust to range [-pi/2, pi/2]
            
            nx = math.cos(lat) * math.cos(lon)
            ny = math.cos(lat) * math.sin(lon)
            nz = math.sin(lat)
            perlin_value = noise.pnoise3(nx * scale, ny * scale, nz * scale, octaves=16, persistence=0.5, lacunarity=2.0)
            
            normalized_value = (perlin_value + 1) / 2
            abs_lat = abs(lat)
            if abs_lat < math.pi / 4:
                coast_threshold = interpolate_value(0.45, 0.425, abs_lat / (math.pi / 4))
            else:
                coast_threshold = 0.425
            
            water_threshold = water_level
            coast_threshold = interpolate_value(water_threshold + 0.05, coast_threshold, abs_lat / (math.pi / 2))
            
            if normalized_value < water_threshold:
                color = interpolate_color((0, 0, 128), (200, 200, 255), normalized_value / water_threshold)
            elif normalized_value < coast_threshold:
                color = interpolate_color((250, 240, 190), (244, 164, 96), (normalized_value - water_threshold) / (coast_threshold - water_threshold))
            elif normalized_value < 0.7:
                base_color = interpolate_color((244, 164, 96), (34, 139, 34), abs_lat / (math.pi / 2))
                color = interpolate_color(base_color, (107, 142, 35), (normalized_value - coast_threshold) / (0.7 - coast_threshold))
            else:
                base_color = interpolate_color((139, 137, 137), (34, 139, 34), abs_lat / (math.pi / 2))
                color = interpolate_color((200,200,200), (255, 255, 255), (normalized_value - 0.7) / (1.0 - 0.7))
            
            if normalized_value >= water_threshold:
                noise_factor = noise.pnoise3(x / 100.0, y / 100.0, seed)
                noise_factor = (noise_factor + 1) / 2
                if abs_lat > 2 * math.pi / 5:
                    color = (255, 250, 250)
                elif abs_lat > math.pi / 4:
                    snow_factor = ((abs_lat - math.pi / 4) / (math.pi / 20)) * noise_factor
                    color = interpolate_color(color, (255, 255, 255), snow_factor)
            
            color_str = ','.join(map(str, color))
            cur.execute("INSERT INTO terrain (x, y, color, height) VALUES (?, ?, ?, ?)", (x, y, color_str, int(normalized_value * 65535)))
    conn.commit()
    print("Terrain data calculation completed.")

# Initialize height multiplier and y pixel offset
height_multiplier = 1000
y_pixel_offset = 0

# Pixel separation factor for isometric projection
pixel_separation = 8

# Create the ttkbootstrap window
root = ttk.Window(themename="darkly")
root.title("Isometric Spherical Terrain Viewer")

# Create a larger canvas widget for the isometric view
canvas = ttk.Canvas(root, width=section_size * pixel_separation, height=section_size * pixel_separation)
canvas.grid(row=0, column=1, padx=10, pady=10)

# Create a smaller canvas widget for the 3D sphere
sphere_canvas = ttk.Canvas(root, width=500, height=500, background="black")
sphere_canvas.grid(row=0, column=0, padx=10, pady=10)

# Create buttons to control panning
btn_frame = ttk.Frame(root)
btn_up = ttk.Button(btn_frame, text="↑", command=lambda: pan(0, -section_size // 10))
btn_down = ttk.Button(btn_frame, text="↓", command=lambda: pan(0, section_size // 10))
btn_left = ttk.Button(btn_frame, text="←", command=lambda: pan(-section_size // 10, 0))
btn_right = ttk.Button(btn_frame, text="→", command=lambda: pan(section_size // 10, 0))

btn_up.grid(row=0, column=1, padx=5, pady=5)
btn_down.grid(row=2, column=1, padx=5, pady=5)
btn_left.grid(row=1, column=0, padx=5, pady=5)
btn_right.grid(row=1, column=2, padx=5, pady=5)
btn_frame.grid(row=1, column=1, pady=10)

# Bind arrow keys for panning
def key_press(event):
    if event.keysym == 'Up':
        pan(0, -section_size // 10)
    elif event.keysym == 'Down':
        pan(0, section_size // 10)
    elif event.keysym == 'Left':
        pan(-section_size // 10, 0)
    elif event.keysym == 'Right':
        pan(section_size // 10, 0)

root.bind('<Up>', key_press)
root.bind('<Down>', key_press)
root.bind('<Left>', key_press)
root.bind('<Right>', key_press)

# Create a slider to adjust the height multiplier
label_height_multiplier = ttk.Label(root, text="Height Multiplier")
label_height_multiplier.grid(row=2, column=1, padx=10, pady=(10, 0))
slider_height_multiplier = ttk.Scale(root, from_=100, to=2000, orient=HORIZONTAL, command=update_height_multiplier)
slider_height_multiplier.set(height_multiplier)
slider_height_multiplier.grid(row=3, column=1, padx=10, pady=5)

# Create a slider to adjust the y pixel offset
label_y_pixel_offset = ttk.Label(root, text="Y Pixel Offset")
label_y_pixel_offset.grid(row=4, column=1, padx=10, pady=(10, 0))
slider_y_pixel_offset = ttk.Scale(root, from_=-section_size//2-200, to=section_size//2+5500, orient=HORIZONTAL, command=update_y_pixel_offset)
slider_y_pixel_offset.set(y_pixel_offset)
slider_y_pixel_offset.grid(row=5, column=1, padx=10, pady=5)

# Create a slider to adjust the pixel separation
label_pixel_separation = ttk.Label(root, text="Pixel Separation")
label_pixel_separation.grid(row=6, column=1, padx=10, pady=(10, 0))
slider_pixel_separation = ttk.Scale(root, from_=1, to=10, orient=HORIZONTAL, command=update_pixel_separation)
slider_pixel_separation.set(pixel_separation)
slider_pixel_separation.grid(row=7, column=1, padx=10, pady=5)

# Initialize the canvas with the first section after the window is fully loaded
root.after(100, update_canvas)
root.after(100, draw_sphere)

# Start the ttkbootstrap main loop
root.mainloop()

# Close the database connection when the application is closed
conn.close()
