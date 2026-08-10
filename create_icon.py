from PIL import Image, ImageDraw

# Create a simple dental icon
size = 256
image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(image)

# Draw a circle
draw.ellipse((20, 20, size-20, size-20), fill=(52, 152, 219, 255))

# Draw a tooth shape (simplified)
draw.rectangle((size//2-30, 40, size//2+30, size-40), fill=(255, 255, 255, 255))
draw.ellipse((size//2-40, 30, size//2+40, 100), fill=(255, 255, 255, 255))
draw.ellipse((size//2-40, size-100, size//2+40, size-30), fill=(255, 255, 255, 255))

# Save as icon
image.save('dental.ico', format='ICO', sizes=[(256, 256)])
print("✅ Icon created: dental.ico")