@echo off
echo Starting QT-Online Local Development Environment...
docker-compose -f docker-compose.yml -f docker-compose.local.yml up -d --build
echo.
echo Local environment is running at: http://localhost
echo.
pause
