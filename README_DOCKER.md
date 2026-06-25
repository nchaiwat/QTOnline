# Docker Deployment Instructions

This project is now set up to run with Docker, using Nginx as a reverse proxy and Gunicorn as the application server.

## Prerequisites
- Docker and Docker Compose installed on your machine (or VPS).

## Structure
- **web**: The Flask application running with Gunicorn.
- **nginx**: The web server that handles incoming requests and forwards them to the Flask app.
- **db**: PostgreSQL database.

## How to Run

1.  **Build and Start the Containers:**
    Open a terminal in the project directory and run:
    ```bash
    docker-compose up -d --build
    ```

2.  **Access the Application:**
    The application will be available at `http://localhost` (or your VPS IP address).

3.  **Database:**
    - The database data is persisted in a Docker volume named `postgres_data`.
    - The database runs on port `5432` inside the network, but is exposed on port `5435` on the host (to avoid conflicts with local Postgres).

4.  **Stopping the Application:**
    ```bash
    docker-compose down
    ```

## Notes
- **Data Migration**: Since this creates a new PostgreSQL container, your existing data from the local Windows PostgreSQL will **NOT** be automatically transferred. You will need to backup your local database and restore it into the Docker container if you want to keep the data.
- **Uploads**: The `instance` folder is mounted as a volume, so uploaded files (images, PDFs) will be preserved on the host machine in the `instance` folder.
