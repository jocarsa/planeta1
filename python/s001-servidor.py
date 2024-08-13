from flask import Flask, send_file, jsonify
from PIL import Image
import sqlite3
import io

app = Flask(__name__)

# Path to your SQLite database
DATABASE_PATH = "datos_terreno.db"

# Function to get terrain data from the database
def get_terrain_data():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT x, y, color, altura FROM terreno")
    terrain_data = cursor.fetchall()
    
    conn.close()
    return terrain_data

# Generate a terrain color map
def generate_terrain_color_map():
    terrain_data = get_terrain_data()

    # Assuming your terrain dimensions
    terrain_width = 2048  # Set this to your terrain's actual width
    terrain_height = 1024  # Set this to your terrain's actual height
    
    color_image = Image.new("RGB", (terrain_width, terrain_height))
    pixels = color_image.load()

    for x, y, color_str, _ in terrain_data:
        if 0 <= x < terrain_width and 0 <= y < terrain_height:
            color = tuple(map(int, color_str.split(',')))
            pixels[x, y] = color
    
    return color_image

# Generate a terrain height map
def generate_terrain_height_map():
    terrain_data = get_terrain_data()

    # Assuming your terrain dimensions
    terrain_width = 2048  # Set this to your terrain's actual width
    terrain_height = 1024  # Set this to your terrain's actual height
    
    height_image = Image.new("L", (terrain_width, terrain_height))
    pixels = height_image.load()

    for x, y, _, altura in terrain_data:
        if 0 <= x < terrain_width and 0 <= y < terrain_height:
            # Normalize height to grayscale (0-255)
            grayscale_value = int((altura / 65535.0) * 255)
            pixels[x, y] = grayscale_value
    
    return height_image

@app.route('/terrain/color_map.jpg')
def terrain_color_map():
    color_image = generate_terrain_color_map()

    # Save the image to a BytesIO object to serve it directly
    img_io = io.BytesIO()
    color_image.save(img_io, 'JPEG')
    img_io.seek(0)
    
    return send_file(img_io, mimetype='image/jpeg')

@app.route('/terrain/height_map.jpg')
def terrain_height_map():
    height_image = generate_terrain_height_map()

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
