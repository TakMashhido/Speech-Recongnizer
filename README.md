# Voice Training and Recognition Web Application

This project is a web application that allows users to record their voice, train a voice profile based on their recordings, and then compare new voice recordings against this profile to get a similarity score. It also supports basic speech-to-text in multiple languages (English, Bengali, Hindi).

## Features

- **Voice Recording**: Record audio directly in the browser.
- **File Upload**: Upload existing audio files (WAV, FLAC, OGG) for processing.
- **Speech Recognition**: Convert spoken audio (from recording or upload) into text. Supports:
    - English (US, UK)
    - Bengali (India)
    - Hindi (India)
- **Custom Filenames**: Users can name their recordings.
- **Voice Profile Training**:
    - List recorded/uploaded audio files.
    - Select specific files to be included in the training set.
    - Train a target voice profile by extracting MFCC features from selected files and averaging them.
    - The trained profile is persisted in a JSON file (`recordings/target_profile.json`) within the Docker volume if mounted.
- **Voice Comparison**:
    - Compare the last processed (recorded/uploaded) voice sample against the trained target profile.
    - Displays Euclidean distance and a similarity score (lower distance / higher similarity indicates a better match).
- **Web Interface**: User-friendly interface built with Flask and vanilla JavaScript.
- **Dockerized**: Comes with a `Dockerfile` for easy setup and deployment.

## Project Structure

```
.
├── gui.py                  # Original Tkinter GUI application (legacy)
├── speech_recongnizer.py   # Original speech recognition script (legacy)
├── webapp/
│   ├── app.py              # Main Flask application logic, API endpoints
│   ├── voice_processing.py # Backend logic for speech recognition & feature extraction
│   ├── Dockerfile          # For building the Docker image
│   ├── requirements.txt    # Python dependencies for the web app
│   ├── recordings/         # Directory for storing audio uploads and target_profile.json (created automatically, ideally mounted as a volume)
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css   # Basic styling for the web interface
│   │   └── js/
│   │       └── main.js     # Frontend JavaScript for recording, API calls, UI updates
│   └── templates/
│       └── index.html      # Main HTML page for the web application
└── README.md               # This file
```

## Technical Stack

- **Backend**: Python, Flask
- **Frontend**: HTML, CSS, JavaScript (vanilla)
- **Speech Recognition**: `speech_recognition` library (using Google Speech Recognition API)
- **Voice Feature Extraction**: `librosa` (for MFCCs)
- **Numerical Operations**: `numpy`
- **Containerization**: Docker

## Setup and Usage

### Prerequisites

- Docker installed and running.
- Web browser with JavaScript enabled and microphone access permissions.

### Running with Docker (Recommended)

1.  **Clone the Repository (if you haven't already)**:
    ```bash
    # git clone <repository_url>
    # cd <repository_name>
    ```

2.  **Navigate to the `webapp` directory**:
    ```bash
    cd webapp
    ```

3.  **Build the Docker Image**:
    ```bash
    docker build -t voice-app-web .
    ```

4.  **Run the Docker Container**:
    To run the container and persist recordings and the trained profile, you should mount a volume to `/app/recordings`. Replace `/path/on/your/host/voice_app_data` with an actual path on your machine where you want to store this data.
    ```bash
    mkdir -p /path/on/your/host/voice_app_data # Create the host directory if it doesn't exist
    docker run -p 5001:5001 -v /path/on/your/host/voice_app_data:/app/recordings voice-app-web
    ```
    If you don't need persistence across container restarts for testing, you can run without the volume mount:
    ```bash
    docker run -p 5001:5001 voice-app-web
    ```

5.  **Access the Application**:
    Open your web browser and go to `http://localhost:5001`.

### Development (Without Docker - requires manual Python environment setup)

1.  **Create a Python Virtual Environment** (recommended):
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

2.  **Install Dependencies**:
    Navigate to the `webapp` directory and install requirements:
    ```bash
    cd webapp
    pip install -r requirements.txt
    ```
    You might also need to install system dependencies like `ffmpeg` and `libsndfile1` manually if not already present:
    ```bash
    # On Debian/Ubuntu:
    # sudo apt-get update && sudo apt-get install ffmpeg libsndfile1
    ```

3.  **Run the Flask Application**:
    From within the `webapp` directory:
    ```bash
    python app.py
    ```

4.  **Access the Application**:
    Open your web browser and go to `http://localhost:5001`.

## How to Use the Web Application

1.  **Language Selection**: Choose the language for speech recognition from the dropdown.
2.  **Record Audio**: Click "Record Audio". Allow microphone permission if prompted. Click "Stop Recording" when done. The recognized text will appear.
3.  **Upload Audio**: Alternatively, choose a WAV, FLAC, or OGG file and click "Upload and Recognize".
4.  **Refresh File List**: After recording/uploading, click "Refresh File List" in the "Train Target Voice Profile" section. Your saved recordings should appear.
5.  **Select Files for Training**: Select one or more files from the list that you want to use to create your voice profile.
6.  **Train Profile**: Click "Train with Selected Files". A voice profile will be generated and saved.
7.  **Compare Voice**: After a profile is trained, record or upload a new audio sample. Once it's recognized, click "Compare Last Processed Audio to Target". The similarity score and distance will be displayed.

## Notes on Voice Profile and Comparison

- **Feature Extraction**: The voice profile is created by extracting Mel-frequency Cepstral Coefficients (MFCCs) from the audio. Specifically, the mean of the MFCC vectors over the duration of each selected audio file is taken. These mean vectors are then averaged across all selected files to create the final `target_voice_profile`.
- **Comparison**: The comparison is done by calculating the Euclidean distance between the MFCC-based feature vector of the new audio and the stored `target_voice_profile`. A lower distance implies greater similarity. A simple similarity score (1 / (1 + distance)) is also provided.
- **Persistence**: The trained profile (`target_profile.json`) and recordings are stored in the `webapp/recordings/` directory. When using Docker, mounting this directory as a volume is essential for data to persist if the container is removed or re-created.

## Legacy GUI

The project also contains `gui.py`, which is the original Tkinter-based desktop application. This application has similar functionalities but is not part of the web deployment. It can be run independently if a desktop environment with Python and necessary libraries (including Tkinter, SpeechRecognition, PyAudio, Librosa, etc.) is set up.

```bash
# To run the legacy GUI (ensure all its specific dependencies are installed):
# python gui.py 
```

## Future Enhancements

- More sophisticated voice activity detection for recording.
- User accounts and personalized voice profiles.
- Advanced similarity metrics and thresholding for verification/identification.
- Support for more audio formats and real-time feedback.
- Integration with more advanced TTS for voice cloning tests (e.g., using Coqui XTTS if environment setup allows).
```
