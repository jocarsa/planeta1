from flask import Flask, send_file, request, jsonify
from PIL import Image
import sqlite3
import io

app = Flask(__name__)

# Path to your SQLite database
DATABASE_PATH = "datos_terreno.db"

# Function to get terrain dimensions (max x and max y)
def get_terrain_dimensions():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT MAX(x), MAX(y) FROM terreno")
    max_x, max_y = cursor.fetchone()
    
    conn.close()
    return max_x + 1, max_y + 1  # Add 1 because coordinates are zero-indexed

# Function to get terrain data from the database
def get_terrain_data():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT x, y, color, altura FROM terreno")
    terrain_data = cursor.fetchall()
    
    conn.close()
    return terrain_data

# Generate a terrain color map with scaling
def generate_terrain_color_map(scale=1):
    terrain_data = get_terrain_data()

    # Automatically detect terrain dimensions
    terrain_width, terrain_height = get_terrain_dimensions()
    
    # Adjust dimensions based on scale
    scaled_width = int(terrain_width / scale)
    scaled_height = int(terrain_height / scale)

    color_image = Image.new("RGB", (scaled_width, scaled_height))
    pixels = color_image.load()

    for x, y, color_str, _ in terrain_data:
        scaled_x = int(x / scale)
        scaled_y = int(y / scale)
        if 0 <= scaled_x < scaled_width and 0 <= scaled_y < scaled_height:
            color = tuple(map(int, color_str.split(',')))
            pixels[scaled_x, scaled_y] = color
    
    return color_image

# Generate a terrain height map with scaling
def generate_terrain_height_map(scale=1):
    terrain_data = get_terrain_data()

    # Automatically detect terrain dimensions
    terrain_width, terrain_height = get_terrain_dimensions()
    
    # Adjust dimensions based on scale
    scaled_width = int(terrain_width / scale)
    scaled_height = int(terrain_height / scale)

    height_image = Image.new("L", (scaled_width, scaled_height))
    pixels = height_image.load()

    for x, y, _, altura in terrain_data:
        scaled_x = int(x / scale)
        scaled_y = int(y / scale)
        if 0 <= scaled_x < scaled_width and 0 <= scaled_y < scaled_height:
            # Normalize height to grayscale (0-255)
            grayscale_value = int((altura / 65535.0) * 255)
            pixels[scaled_x, scaled_y] = grayscale_value
    
    return height_image

@app.route('/terrain/color_map.jpg')
def terrain_color_map():
    # Get the scale parameter from the request query string (default to 1)
    scale = float(request.args.get('scale', 1))
    color_image = generate_terrain_color_map(scale)

    # Save the image to a BytesIO object to serve it directly
    img_io = io.BytesIO()
    color_image.save(img_io, 'JPEG')
    img_io.seek(0)
    
    return send_file(img_io, mimetype='image/jpeg')

@app.route('/terrain/height_map.jpg')
def terrain_height_map():
    # Get the scale parameter from the request query string (default to 1)
    scale = float(request.args.get('scale', 1))
    height_image = generate_terrain_height_map(scale)

    # Save the image to a BytesIO object to serve it directly
    img_io = io.BytesIO()
    height_image.save(img_io, 'JPEG')
    img_io.seek(0)
    
    return send_file(img_io, mimetype='image/jpeg')

@app.route('/')
def index():
    return jsonify({"message": "Welcome to the Terrain Data API!"})

if __name__ == '__main__':
    app.run(debug=True)
