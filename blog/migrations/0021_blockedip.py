# Generated by Django 4.2.17 on 2025-01-23 02:29

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0020_chatmessage'),
    ]

    operations = [
        migrations.CreateModel(
            name='BlockedIP',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ip_address', models.GenericIPAddressField(unique=True)),
                ('reason', models.TextField(blank=True)),
                ('date_blocked', models.DateTimeField(default=django.utils.timezone.now)),
                ('is_permanent', models.BooleanField(default=False)),
                ('expires', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'blocked_ips',
            },
        ),
    ]
