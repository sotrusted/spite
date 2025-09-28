# Generated manually to make share_id unique and not null

from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0047_populate_share_ids'),
    ]

    operations = [
        migrations.AlterField(
            model_name='aichatsession',
            name='share_id',
            field=models.CharField(db_index=True, max_length=32, unique=True),
        ),
    ]
