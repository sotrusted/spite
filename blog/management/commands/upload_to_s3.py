from django.core.management.base import BaseCommand
from django.conf import settings
import boto3
import os
from botocore.exceptions import ClientError
from pathlib import Path

class Command(BaseCommand):
    help = 'Upload images to S3 bucket'

    def add_arguments(self, parser):
        parser.add_argument('local_path', type=str, help='Local path to image(s)')
        parser.add_argument('--prefix', type=str, help='S3 folder prefix', default='')
        parser.add_argument('--recursive', action='store_true', help='Upload directory recursively')

    def handle(self, *args, **options):
        if not hasattr(settings, 'AWS_STORAGE_BUCKET_NAME'):
            self.stdout.write(self.style.ERROR('AWS_STORAGE_BUCKET_NAME not found in settings'))
            return

        # Initialize S3 client using Django settings
        s3_client = boto3.client('s3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )

        local_path = Path(options['local_path'])
        bucket = settings.AWS_STORAGE_BUCKET_NAME
        prefix = options['prefix']

        self.stdout.write(f'Using bucket: {bucket}')

        if local_path.is_file():
            # Upload single file
            self._upload_file(s3_client, local_path, bucket, prefix)
        elif local_path.is_dir() and options['recursive']:
            # Upload directory recursively
            self._upload_directory(s3_client, local_path, bucket, prefix)
        else:
            self.stdout.write(self.style.ERROR('Invalid path or missing --recursive flag for directory'))

    def _upload_file(self, s3_client, file_path, bucket, prefix):
        try:
            # Construct S3 key (path in bucket)
            s3_key = f"{prefix}/{file_path.name}" if prefix else file_path.name
            
            # Upload file with content type detection
            content_type = self._get_content_type(file_path)
            
            s3_client.upload_file(
                str(file_path),
                bucket,
                s3_key,
                ExtraArgs={
                    'ContentType': content_type,
                    'ACL': 'public-read'
                }
            )
            
            # Generate the S3 URL for the uploaded file
            s3_url = f"https://{bucket}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{s3_key}"
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully uploaded {file_path}\nS3 URL: {s3_url}')
            )
            
        except ClientError as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to upload {file_path}: {str(e)}')
            )

    def _upload_directory(self, s3_client, directory, bucket, prefix):
        total_files = len(list(directory.rglob('*')))
        processed_files = 0
        
        for item in directory.rglob('*'):
            if item.is_file():
                processed_files += 1
                # Calculate relative path for S3 key
                relative_path = item.relative_to(directory)
                s3_key = f"{prefix}/{relative_path}" if prefix else str(relative_path)
                
                self.stdout.write(f'Uploading {processed_files}/{total_files}: {item.name}')
                self._upload_file(s3_client, item, bucket, os.path.dirname(s3_key))

    def _get_content_type(self, file_path):
        """Determine content type based on file extension"""
        extension = file_path.suffix.lower()
        content_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.svg': 'image/svg+xml',
        }
        return content_types.get(extension, 'application/octet-stream') 