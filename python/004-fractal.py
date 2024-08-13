from PIL import Image
import random
import os
import time
from colorsys import hsv_to_rgb

# Create the render directory if it doesn't exist
output_dir = "render"
os.makedirs(output_dir, exist_ok=True)

# Function to generate a fractal image with variations in value and saturation
def generate_fractal_image(hue, width=192, height=108, max_iter=100):
    image = Image.new("RGB", (width, height))
    
    for x in range(width):
        for y in range(height):
            # Normalize the coordinates to be in the range of the fractal
            zx, zy = x * 3.0 / width - 1.5, y * 2.0 / height - 1.0
            c = complex(zx, zy)
            z = complex(0, 0)
            for i in range(max_iter):
                if abs(z) > 2.0:
                    break
                z = z*z + c
            
            # Use the number of iterations to determine saturation and value
            saturation = 1.0 if i < max_iter else 0.0
            value = i / max_iter if i < max_iter else 0.0
            
            # Convert HSV to RGB
            r, g, b = hsv_to_rgb(hue, saturation, value)
            r, g, b = int(r * 255), int(g * 255), int(b * 255)
            
            image.putpixel((x, y), (r, g, b))
    
    return image

# Generate and save 10 images
for _ in range(10):
    # Select a random hue
    hue = random.random()
    
    # Generate the fractal image with the selected hue
    image = generate_fractal_image(hue)

    # Scale the image to 1920x1080 without antialiasing
    scaled_image = image.resize((1920, 1080), Image.Resampling.NEAREST)

    # Save the scaled image with the current epoch time as the filename
    epoch_time = int(time.time())
    filename = os.path.join(output_dir, f"{epoch_time}.png")
    scaled_image.save(filename)

    # Wait a second to ensure unique filenames
    time.sleep(1)
