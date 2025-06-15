# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
# Ensure this path is correct relative to the build context (project root)
COPY backend/requirements.txt ./requirements.txt

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend application code into the container at /app/backend
COPY ./backend/ ./backend/
# Copy the worker code as it's imported by path in RQ and metadata_manager is in backend
COPY ./worker/ ./worker/
# file_metadata.json will be volume mounted, not copied.

# Make port 5000 available
EXPOSE 5000

# Define environment variables
ENV PYTHONUNBUFFERED 1
ENV FLASK_APP backend/app.py
ENV FLASK_RUN_HOST 0.0.0.0
ENV FLASK_RUN_PORT 5000
ENV REDIS_HOST redis
ENV REDIS_PORT 6379

# Run app.py when the container launches using flask command
CMD ["flask", "run"]
