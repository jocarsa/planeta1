import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import sqlite3
import numpy as np
import noise
import random
import math

# Set the dimensions for the equirectangular projection
multiplicador = 1024
multiplica = 8
width, height = multiplicador * multiplica * 2, multiplicador * multiplica
scale = 5
cloud_scale = 7  # Different scale for clouds
water_level = 0.5  # Default water level, can be adjusted

# Initialize seed
seed = random.randint(0, 1000000)

# Define the section size for the larger canvas
section_size = int(math.sqrt(0.00001 * width * height)) * 2  # Increase the section size by a factor of 2

# Define the starting points for the section at the center of the terrain
x_start = (width - section_size) // 2
y_start = (height - section_size) // 2

# Function to convert terrain coordinates to spherical coordinates
def terrain_to_spherical(x, y, width, height):
    lon = (x / width) * 2 * math.pi  # Longitude in [0, 2pi]
    lat = (y / height) * math.pi  # Latitude in [0, pi]
    lat = lat - math.pi / 2  # Adjust to range [-pi/2, pi/2]
    return lat, lon

# Function to initialize the database
def init_db():
    conn = sqlite3.connect("terrain_data.db")
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS terrain (x INTEGER, y INTEGER, color TEXT, height INTEGER, PRIMARY KEY (x, y))")
    cur.execute("CREATE TABLE IF NOT EXISTS clouds (x INTEGER, y INTEGER, color TEXT, height INTEGER, PRIMARY KEY (x, y))")
    return conn, cur

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

# Pre-calculate the cloud data if not already done
if cur.execute("SELECT COUNT(*) FROM clouds").fetchone()[0] == 0:
    print("Calculating cloud data. This may take a while...")
    for x in range(width):
        for y in range(height):
            # Generate Perlin noise value for the cloud layer
            lon = (x / width) * 2 * math.pi  # Longitude in [0, 2pi]
            lat = (y / height) * math.pi  # Latitude in [0, pi]
            lat = lat - math.pi / 2  # Adjust to range [-pi/2, pi/2]
            
            nx = math.cos(lat) * math.cos(lon)
            ny = math.cos(lat) * math.sin(lon)
            nz = math.sin(lat)
            perlin_value = noise.pnoise3(nx * cloud_scale, ny * cloud_scale, nz * cloud_scale, octaves=8, persistence=0.5, lacunarity=2.0)
            
            normalized_value = (perlin_value + 1) / 2
            color = interpolate_color((255, 255, 255), (200, 200, 200), normalized_value)
            
            color_str = ','.join(map(str, color))
            cur.execute("INSERT INTO clouds (x, y, color, height) VALUES (?, ?, ?, ?)", (x, y, color_str, int(normalized_value * 65535)))
    conn.commit()
    print("Cloud data calculation completed.")

def interpolate_color(color1, color2, factor):
    return tuple(int(a + (b - a) * factor) for a, b in zip(color1, color2))

def interpolate_value(val1, val2, factor):
    return val1 + (val2 - val1) * factor

def darken_color(color, factor):
    return tuple(int(c * (1 - factor)) for c in color)

# OpenGL rendering setup
def setup_opengl():
    glEnable(GL_DEPTH_TEST)
    glShadeModel(GL_SMOOTH)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

def draw_terrain():
    global x_start, y_start, section_size, width, height, scale, seed, water_level, cur
    x_end = x_start + section_size
    y_end = y_start + section_size
    
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    gluLookAt(0, 1500, 1500, 0, 0, 0, 0, 1, 0)
    
    # Batch fetch data from database
    cur.execute("SELECT x, y, color, height FROM terrain WHERE x BETWEEN ? AND ? AND y BETWEEN ? AND ?",
                (x_start, x_end - 1, y_start, y_end - 1))
    terrain_data = cur.fetchall()
    
    cur.execute("SELECT x, y, color, height FROM clouds WHERE x BETWEEN ? AND ? AND y BETWEEN ? AND ?",
                (x_start, x_end - 1, y_start, y_end - 1))
    cloud_data = cur.fetchall()
    
    # Convert data to a dictionary for quick access
    terrain_dict = {(x, y): (color_str, height) for x, y, color_str, height in terrain_data}
    cloud_dict = {(x, y): (color_str, height) for x, y, color_str, height in cloud_data}
    
    glBegin(GL_QUADS)
    for x in range(x_start, x_end):
        for y in range(y_start, y_end):
            if (x, y) not in terrain_dict:
                continue
            
            color_str, height = terrain_dict[(x, y)]
            color = tuple(map(int, color_str.split(',')))
            glColor3ub(*color)
            
            normalized_value = height / 65535.0
            iso_x = (x - x_start) * 10
            iso_y = (y - y_start) * 10
            z = normalized_value * 100
            
            glVertex3f(iso_x, iso_y, z)
            glVertex3f(iso_x + 10, iso_y, z)
            glVertex3f(iso_x + 10, iso_y + 10, z)
            glVertex3f(iso_x, iso_y + 10, z)
    glEnd()

    pygame.display.flip()

# Initialize Pygame and OpenGL
def main():
    global x_start, y_start, width, height, section_size
    pygame.init()
    screen = pygame.display.set_mode((800, 600), DOUBLEBUF | OPENGL)
    pygame.display.set_caption("3D Terrain")
    
    setup_opengl()
    
    clock = pygame.time.Clock()
    running = True
    
    while running:
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == KEYDOWN:
                if event.key == K_UP:
                    y_start = (y_start - section_size // 10) % height
                elif event.key == K_DOWN:
                    y_start = (y_start + section_size // 10) % height
                elif event.key == K_LEFT:
                    x_start = (x_start - section_size // 10) % width
                elif event.key == K_RIGHT:
                    x_start = (x_start + section_size // 10) % width
        
        draw_terrain()
        clock.tick(30)
    
    pygame.quit()

if __name__ == "__main__":
    main()
