from PIL import Image
import random
import os
import time

# Create the render directory if it doesn't exist
output_dir = "render"
os.makedirs(output_dir, exist_ok=True)

# Generate and save 10 images
for _ in range(10):
    # Create an image with random colors
    width, height = 192, 108
    image = Image.new("RGB", (width, height))
    for x in range(width):
        for y in range(height):
            image.putpixel((x, y), (
                random.randint(0, 255), 
                random.randint(0, 255), 
                random.randint(0, 255)
            ))

    # Scale the image to 1920x1080 without antialiasing
    scaled_image = image.resize((1920, 1080), Image.Resampling.NEAREST)

    # Save the scaled image with the current epoch time as the filename
    epoch_time = int(time.time())
    filename = os.path.join(output_dir, f"{epoch_time}.png")
    scaled_image.save(filename)

    # Wait a second to ensure unique filenames
    time.sleep(1)
