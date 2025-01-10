from django.core.management.base import BaseCommand
from blog.models import Post
from django.conf import settings
import os
import logging
from PIL import Image
import io
import boto3
from urllib.parse import unquote

logger = logging.getLogger('spite')

class Command(BaseCommand):
    help = 'Normalize and compress media files to standard sizes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--max-size',
            type=int,
            default=1920,
            help='Maximum dimension (width or height) for images'
        )
        parser.add_argument(
            '--quality',
            type=int,
            default=85,
            help='JPEG compression quality (1-100)'
        )

    def handle(self, *args, **options):
        max_size = options['max_size']
        quality = options['quality']
        
        # Initialize S3 client if using S3
        s3_client = None
        if settings.DEFAULT_FILE_STORAGE == 'storages.backends.s3boto3.S3Boto3Storage':
            s3_client = boto3.client('s3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME
            )

        # Get all posts with media
        posts = Post.objects.filter(media_file__isnull=False) | Post.objects.filter(image__isnull=False)
        total_posts = posts.count()
        logger.info(f"Found {total_posts} posts with media to process")

        for index, post in enumerate(posts, 1):
            try:
                # Get the appropriate file field
                if getattr(post, 'media_file', None):
                    file_field = post.media_file
                elif getattr(post, 'image', None):
                    file_field = post.image
                else:
                    continue

                # Skip videos
                if getattr(post, 'is_video', lambda: False)():
                    logger.info(f"Skipping video post {post.id}")
                    continue

                logger.info(f"Processing {index}/{total_posts}: Post {post.id}")

                # Get image data
                img_data = None
                if s3_client:
                    try:
                        s3_key = file_field.name
                        file_obj = io.BytesIO()
                        s3_client.download_fileobj(
                            settings.AWS_STORAGE_BUCKET_NAME,
                            s3_key,
                            file_obj
                        )
                        img_data = file_obj.getvalue()
                    except Exception as e:
                        logger.error(f"Failed to download from S3: {str(e)}")
                else:
                    try:
                        with open(file_field.path, 'rb') as f:
                            img_data = f.read()
                    except Exception as e:
                        logger.error(f"Failed to read local file: {str(e)}")

                if not img_data:
                    continue

                # Process the image
                img = Image.open(io.BytesIO(img_data))
                
                # Convert RGBA to RGB if necessary
                if img.mode in ('RGBA', 'LA'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')

                # Resize if needed
                if max(img.size) > max_size:
                    ratio = max_size / max(img.size)
                    new_size = tuple(int(dim * ratio) for dim in img.size)
                    img = img.resize(new_size, Image.Resampling.LANCZOS)

                # Save compressed image
                output = io.BytesIO()
                img.save(output, format='JPEG', quality=quality, optimize=True)
                output.seek(0)

                # Get original image size for logging
                original_size = len(img_data)
                
                # Get compressed size for logging
                compressed_data = output.getvalue()
                compressed_size = len(compressed_data)
                
                # Save back to storage
                if s3_client:
                    try:
                        s3_client.upload_fileobj(
                            output,
                            settings.AWS_STORAGE_BUCKET_NAME,
                            file_field.name,
                            ExtraArgs={'ContentType': 'image/jpeg'}
                        )
                        logger.info(f"Saved compressed image to S3: {file_field.name}")
                        logger.info(f"Size reduced from {original_size/1024:.1f}KB to {compressed_size/1024:.1f}KB")
                        successfully_normalized.add(post.id)
                    except Exception as e:
                        logger.error(f"Failed to upload to S3: {str(e)}")
                else:
                    try:
                        with open(file_field.path, 'wb') as f:
                            f.write(output.getvalue())
                        logger.info(f"Saved compressed image locally: {file_field.path}")
                        logger.info(f"Size reduced from {original_size/1024:.1f}KB to {compressed_size/1024:.1f}KB")
                        successfully_normalized.add(post.id)
                    except Exception as e:
                        logger.error(f"Failed to save local file: {str(e)}")

                n += 1
                # Save progress periodically
                if n % 10 == 0:
                    normalized_ids.update(successfully_normalized)
                    with open(normalized_path, 'w') as f:
                        json.dump(list(normalized_ids), f)
                    logger.info(f"Progress saved: {n}/{total_posts} items processed")

            except Exception as e:
                logger.error(f"Error processing post {post.id}: {str(e)}", exc_info=True)
                continue

        # Final save of normalized images list
        normalized_ids.update(successfully_normalized)
        with open(normalized_path, 'w') as f:
            json.dump(list(normalized_ids), f)

        logger.info(f"Image normalization complete. Successfully processed {len(successfully_normalized)} images") 