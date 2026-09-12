import pytesseract
from PIL import Image

# Point this at any image with text on it
img = Image.open("./assets/test-1.png")
print(pytesseract.image_to_string(img))