import os
from PIL import Image

UPLOAD_FOLDER = 'static/images/products/'
RESIZED_FOLDER = 'static/images/resized/'

os.makedirs(RESIZED_FOLDER, exist_ok=True)

def resize_image(image_path, size=(100, 100)):
    if not image_path or not os.path.exists(image_path):
        return None

    filename = os.path.basename(image_path)
    resized_filename = f"resized_{filename}"
    resized_path = os.path.join(RESIZED_FOLDER, resized_filename)

    if os.path.exists(resized_path):
        return resized_path

    try:
        with Image.open(image_path) as img:
            img = img.resize(size, Image.Resampling.LANCZOS)
            img.save(resized_path)
        return resized_path
    except Exception as e:
        print(f"Error resizing image: {e}")
        return None