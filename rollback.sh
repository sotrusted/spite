#!/bin/bash
# Stop Docker containers
docker-compose down

# Restore database
psql spite < spite_backup.sql

# Restore media files
tar -xzf media_backup.tar.gz

# Restore supervisor config
sudo cp supervisor_backup.conf /etc/supervisor/conf.d/spite.conf

# Restart services
sudo systemctl restart nginx redis-server memcached
sudo supervisorctl reload
