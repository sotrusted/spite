from django.core.management.base import BaseCommand
from blog.models import Post
import cv2
import numpy as np
import json
from django.conf import settings
import os
import logging
from urllib.parse import unquote
import boto3
import io

logger = logging.getLogger('spite')

class Command(BaseCommand):
    help = 'Process all media files and store their OpenCV features'

    def handle(self, *args, **kwargs):
        features_dir = os.path.join(settings.MEDIA_ROOT, 'features')
        os.makedirs(features_dir, exist_ok=True)
        
        # Load existing features if available
        features_path = os.path.join(features_dir, 'media_features.json')
        features_data = []
        processed_ids = set()
        
        if os.path.exists(features_path):
            try:
                with open(features_path, 'r') as f:
                    features_data = json.load(f)
                    processed_ids = {item['id'] for item in features_data}
                logger.info(f"Loaded {len(processed_ids)} existing processed items")
            except Exception as e:
                logger.error(f"Error loading existing features: {str(e)}")
                features_data = []
                processed_ids = set()
        
        posts = Post.objects.filter(media_file__isnull=False) | Post.objects.filter(image__isnull=False)
        # Filter out already processed posts
        logger.info(f"{len(posts)} posts to process")
        posts = posts.exclude(id__in=processed_ids)
        logger.info(f"{len(processed_ids)} posts already processed")
        total_posts = posts.count()
        
        logger.info(f"Starting media processing for {total_posts} new posts with media")
        
        # Initialize S3 client
        s3_client = boto3.client('s3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )

        n=0
        
        for index, post in enumerate(posts, 1):
            try:
                # Debug path resolution
                if getattr(post, 'media_file', None):
                    file_field = post.media_file
                    media_url = post.media_file.url
                elif getattr(post, 'image', None):
                    file_field = post.image
                    media_url = post.image.url
                else:
                    continue

                # Get file name and fix path if needed
                file_name = file_field.name
                if 'images/' in file_name:
                    # Convert old 'images/' path to 'media/'
                    file_name = file_name.replace('images/', 'media/')
                    logger.info(f"Converted old images path to: {file_name}")

                # Try to read the file
                file_path = os.path.join(settings.MEDIA_ROOT, file_name)
                logger.info(f"Attempting to read: {file_path}")

                # Try to read image from S3 first, then fallback to local
                img = None
                if settings.DEFAULT_FILE_STORAGE == 'storages.backends.s3boto3.S3Boto3Storage':
                    try:
                        # Extract bucket path from the URL
                        s3_key = file_field.name
                        logger.info(f"Attempting to read from S3: {s3_key}")
                        
                        # Download file from S3 to memory
                        file_byte_string = io.BytesIO()
                        s3_client.download_fileobj(
                            settings.AWS_STORAGE_BUCKET_NAME,
                            s3_key,
                            file_byte_string
                        )
                        
                        # Convert to numpy array
                        file_bytes = np.asarray(bytearray(file_byte_string.getvalue()), dtype=np.uint8)
                        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                        
                        if img is not None:
                            logger.info(f"Successfully read image from S3: {s3_key}")
                    except Exception as e:
                        logger.warning(f"Failed to read from S3: {str(e)}")

                # Fallback to local paths if S3 failed or not configured
                if img is None:
                    for path in paths_to_try:
                        logger.info(f"Trying to read local file: {path}")
                        img = cv2.imread(path)
                        if img is not None:
                            logger.info(f"Successfully read image from local path: {path}")
                            break

                if img is None:
                    logger.warning(f"Could not read media file for post {post.id} from any path")
                    continue

                # Convert to grayscale
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                
                # Use SIFT for feature detection
                sift = cv2.SIFT_create()
                keypoints, descriptors = sift.detectAndCompute(gray, None)
                
                if descriptors is not None:
                    # Calculate average descriptor
                    avg_descriptor = np.mean(descriptors, axis=0).tolist()
                    
                    # Store features
                    features_data.append({
                        'id': post.id,
                        'url': media_url,
                        'type': 'video' if getattr(post, 'is_video', lambda: False)() else 'image',
                        'features': avg_descriptor
                    })
                    
                    logger.info(f"Successfully processed post {post.id}")
                else:
                    logger.warning(f"No features detected for post {post.id}")
                
            except Exception as e:
                logger.error(f"Error processing post {post.id}: {str(e)}", exc_info=True)
                continue

            n+=1 
            # Save progress periodically
            if n % 10 == 0:
                features_path = os.path.join(features_dir, 'media_features.json')
                with open(features_path, 'w') as f:
                    json.dump(features_data, f)
                logger.info(f"Progress saved: {index}/{total_posts} items processed")

        # Final save
        features_path = os.path.join(features_dir, 'media_features.json')
        with open(features_path, 'w') as f:
            json.dump(features_data, f)
        
        logger.info(f'Successfully processed {len(features_data)} media items')