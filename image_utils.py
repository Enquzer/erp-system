# image_utils.py
import os
from PIL import Image

# Define directories
UPLOAD_FOLDER = 'static/images/products/'
RESIZED_FOLDER = 'static/images/resized/'

# Ensure the resized folder exists
os.makedirs(RESIZED_FOLDER, exist_ok=True)

def resize_image(image_path, size=(100, 100)):
    """
    Resize an image to the specified size and save it to the resized folder.
    Returns the path to the resized image, relative to the static directory.
    """
    if not image_path:
        print(f"No image path provided")
        return None

    # Ensure the image path is absolute for file operations
    if not os.path.isabs(image_path):
        image_path = os.path.join(os.getcwd(), image_path)

    if not os.path.exists(image_path):
        print(f"Image does not exist at path: {image_path}")
        return None

    # Generate a unique filename for the resized image
    filename = os.path.basename(image_path)
    resized_filename = f"resized_{filename}"
    resized_path = os.path.join(RESIZED_FOLDER, resized_filename)

    # Skip if the resized image already exists
    if os.path.exists(resized_path):
        relative_path = os.path.join('images', 'resized', resized_filename)
        print(f"Resized image already exists: {relative_path}")
        return relative_path

    # Open and resize the image
    try:
        with Image.open(image_path) as img:
            img = img.resize(size, Image.Resampling.LANCZOS)
            img.save(resized_path)
        relative_path = os.path.join('images', 'resized', resized_filename)
        print(f"Resized image saved: {relative_path}")
        return relative_path
    except Exception as e:
        print(f"Error resizing image {image_path}: {e}")
        return None

def resize_product_images(products):
    """
    Resize images for a list of products and return a dictionary mapping product IDs to resized image paths.
    """
    resized_images = {}
    for product in products:
        image_path = product['product_image']
        print(f"Processing product {product['product_id']}, image path: {image_path}")
        if image_path:
            resized_path = resize_image(image_path)
            if resized_path:
                resized_images[product['product_id']] = resized_path
            else:
                print(f"Failed to resize image for product {product['product_id']}")
        else:
            print(f"No image path for product {product['product_id']}")
    return resized_images