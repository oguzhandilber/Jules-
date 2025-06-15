# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY worker/requirements.txt ./requirements.txt

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install ffmpeg (system dependency for the worker)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Copy the worker application code into the container at /app/worker
COPY ./worker/ ./worker/
# Copy the backend code because worker_process.py imports from backend.metadata_manager
COPY ./backend/ ./backend/
# file_metadata.json will be volume mounted.

# Define environment variables
ENV PYTHONUNBUFFERED 1
ENV REDIS_HOST redis
ENV REDIS_PORT 6379

# Run worker_process.py when the container launches
CMD ["python", "worker/worker_process.py"]
