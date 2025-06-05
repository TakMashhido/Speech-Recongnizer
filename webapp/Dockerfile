# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Install system dependencies for audio processing:
# ffmpeg: For broad audio format support by SpeechRecognition/pydub if needed, and general audio manipulation.
# libsndfile1: A dependency for the 'soundfile' library, which librosa uses to load audio files.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# --no-cache-dir helps in reducing the final image size by not storing the pip download cache.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
# This includes app.py, voice_processing.py, templates/, and static/
COPY . .

# Make port 5001 available to the world outside this container
# This informs Docker that the application inside the container will listen on this port.
EXPOSE 5001

# Define environment variables for Flask
# FLASK_APP tells Flask where our application instance is located (in app.py).
# FLASK_RUN_HOST=0.0.0.0 makes the server listen on all available network interfaces,
# which is necessary for it to be accessible from outside the container.
# FLASK_RUN_PORT specifies the port Flask's development server will use, matching the EXPOSE directive.
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5001
# For development, debug mode can be enabled by setting ENV FLASK_DEBUG=1.
# Alternatively, app.run(debug=True) is used in app.py for direct execution,
# but `flask run` (used by CMD) respects FLASK_DEBUG.

# Data Persistence Note:
# The /app/recordings directory (UPLOAD_FOLDER) will be created by app.py if it doesn't exist
# inside the container. This directory stores uploaded audio files and the 'target_profile.json'.
# To persist these files across container restarts or different container instances,
# a Docker volume should be mounted at this location during `docker run`. For example:
#   docker run -v /path/on/host/recordings:/app/recordings voice-app-web
# This maps a directory on the host to /app/recordings inside the container.

# Run app.py when the container launches using Flask's built-in development server.
# For production deployments, a more robust WSGI server like Gunicorn or uWSGI should be used.
CMD ["flask", "run"]
