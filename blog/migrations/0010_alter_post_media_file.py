# Generated by Django 5.1.3 on 2024-11-27 22:35

import blog.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0009_alter_post_media_file'),
    ]

    operations = [
        migrations.AlterField(
            model_name='post',
            name='media_file',
            field=models.FileField(blank=True, max_length=255, null=True, upload_to='media/', validators=[blog.models.validate_media_file, blog.models.validate_video_file_size], verbose_name='Image or video (<50 MB)'),
        ),
    ]
