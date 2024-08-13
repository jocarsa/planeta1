from PIL import Image
import random

# Create an image with random colors
width, height = 192, 108
image = Image.new("RGB", (width, height))

# Fill the image with random colors
for x in range(width):
    for y in range(height):
        image.putpixel((x, y), (
            random.randint(0, 255), 
            random.randint(0, 255), 
            random.randint(0, 255)
        ))

# Scale the image to 1920x1080 without antialiasing
scaled_image = image.resize((1920, 1080), Image.Resampling.NEAREST)

# Save the scaled image
scaled_image.save("random_color_image.png")

# Display the scaled image
scaled_image.show()
