import requests

# URL
url = 'https://spite.fr/post/new'

# File to upload
file_path = 'media/media/sp1teadmin.png'  # Replace with actual file path

# Form data
data = {
    'title': 'Test Post Title',
    'content': 'Test post content',
    'display_name': 'Test User'
}

# Open file and create files dict
files = {
    'media_file': ('test_image.jpg', open(file_path, 'rb'), 'image/jpeg')
}

try:
    # Send POST request
    response = requests.post(
        url,
        data=data,
        files=files,
        timeout=30  # 30 second timeout
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
except Exception as e:
    print(f"Error: {e}")

finally:
    # Make sure to close the file
    files['media_file'][1].close()