import os
import pandas as pd
from django.core.management.base import BaseCommand
from django.apps import apps
from django.utils import timezone

class Command(BaseCommand):
    help = 'Export Post and Comment models to CSV files using pandas'

    def add_arguments(self, parser):
        parser.add_argument('--output-dir', type=str, default='csv_exports',
                            help='Directory where CSV files will be saved')

    def handle(self, *args, **options):
        output_dir = options['output_dir']
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Get timestamp for filenames
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        
        # Export Posts
        Post = apps.get_model('blog', 'Post')
        self.export_model_to_csv(
            Post, 
            os.path.join(output_dir, f'posts_{timestamp}.csv')
        )
        
        # Export Comments
        Comment = apps.get_model('blog', 'Comment')
        self.export_model_to_csv(
            Comment, 
            os.path.join(output_dir, f'comments_{timestamp}.csv')
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully exported data to {output_dir}')
        )
    
    def export_model_to_csv(self, model, filepath):
        queryset = model.objects.all()
        if not queryset.exists():
            self.stdout.write(
                self.style.WARNING(f'No {model.__name__} records found to export')
            )
            return
        
        # For Comment model, handle foreign keys
        if model.__name__ == 'Comment':
            # Get all data as dictionaries
            data = []
            for comment in queryset:
                comment_dict = {
                    field.name: getattr(comment, field.name) 
                    for field in model._meta.fields 
                    if not field.is_relation
                }
                # Add the post ID and title
                comment_dict['post_id'] = comment.post.id if comment.post else None
                comment_dict['post_title'] = comment.post.title if comment.post else None
                
                # Add parent comment information
                comment_dict['parent_comment_id'] = comment.parent_comment.id if comment.parent_comment else None
                
                data.append(comment_dict)
        else:
            # For other models, just convert to dictionaries
            data = []
            for obj in queryset:
                obj_dict = {}
                for field in model._meta.fields:
                    value = getattr(obj, field.name)
                    # Convert foreign keys to their ID
                    if field.is_relation:
                        if value is not None:
                            value = value.id
                    obj_dict[field.name] = value
                data.append(obj_dict)
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Export to CSV
        df.to_csv(filepath, index=False)
        
        self.stdout.write(
            self.style.SUCCESS(f'Exported {len(df)} {model.__name__} records to {filepath}')
        )