#!/bin/bash
echo "=== 1. Container Status ==="
docker ps -a | grep po-online-app

echo -e "\n=== 2. Last 20 lines of Error Logs ==="
docker logs --tail 20 po-online-app

echo -e "\n=== 3. Checking if Port 8080 is already in use by another process ==="
sudo lsof -i :8080 || echo "Port 8080 is free"

echo -e "\n=== 4. Checking if app.py exists in the directory ==="
ls -l /var/www/po-online/app.py
