document.addEventListener('DOMContentLoaded', function() {
    // UI Element Selectors
    const recordButton = document.getElementById('recordButton');
    const stopButton = document.getElementById('stopButton');
    const uploadButton = document.getElementById('uploadButton');
    const audioFileInput = document.getElementById('audioFile');
    const languageSelect = document.getElementById('language');
    const statusDisplay = document.getElementById('status');
    const recognizedTextArea = document.getElementById('recognizedText');

    const refreshFilesButton = document.getElementById('refreshFilesButton');
    const fileListSelect = document.getElementById('fileList');
    const trainButton = document.getElementById('trainButton');

    // New UI Elements for Comparison
    const compareButton = document.getElementById('compareButton');
    const comparisonResultDisplay = document.getElementById('comparisonResultDisplay');

    // State variables
    let mediaRecorder;
    let audioChunks = [];
    let lastProcessedFilenameForComparison = null; // Stores filename from server after successful recognition/upload

    // --- Check for MediaRecorder support ---
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        statusDisplay.textContent = 'Critical Error: getUserMedia not supported on your browser!';
        recordButton.disabled = true;
        trainButton.disabled = true;
        compareButton.disabled = true;
        return;
    }

    // --- Utility to update button states ---
    function setControlsState(isProcessing) {
        recordButton.disabled = isProcessing;
        // Stop button is handled more specifically during recording
        if (!isProcessing && mediaRecorder && mediaRecorder.state === "inactive") {
             stopButton.disabled = true;
        } else if (mediaRecorder && media_recorder.state === "recording") {
            stopButton.disabled = false;
        }


        uploadButton.disabled = isProcessing;
        trainButton.disabled = isProcessing;
        languageSelect.disabled = isProcessing;
        refreshFilesButton.disabled = isProcessing;
        fileListSelect.disabled = isProcessing;
        // Compare button is enabled only if lastProcessedFilenameForComparison is set AND not processing
        compareButton.disabled = isProcessing || !lastProcessedFilenameForComparison;
    }


    // --- Recording Logic ---
    recordButton.addEventListener('click', async () => {
        if (!mediaRecorder || mediaRecorder.state === "inactive") {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                const mimeTypes = ['audio/webm;codecs=opus', 'audio/ogg;codecs=opus', 'audio/wav'];
                let selectedMimeType = mimeTypes.find(type => MediaRecorder.isTypeSupported(type)) || '';

                if (!selectedMimeType && MediaRecorder.isTypeSupported('')) {
                    selectedMimeType = '';
                } else if (!selectedMimeType) {
                    alert('Your browser does not support a suitable audio format for recording.');
                    statusDisplay.textContent = 'No supported audio format for recording.';
                    return;
                }
                console.log("Using MIME type for recording:", selectedMimeType || "browser default");

                mediaRecorder = new MediaRecorder(stream, { mimeType: selectedMimeType });
                audioChunks = [];

                mediaRecorder.ondataavailable = event => {
                    if (event.data.size > 0) audioChunks.push(event.data);
                };

                mediaRecorder.onstop = () => {
                    const finalMimeType = selectedMimeType || (audioChunks.length > 0 ? audioChunks[0].type : 'application/octet-stream');
                    const recordedAudioBlob = new Blob(audioChunks, { type: finalMimeType });
                    stream.getTracks().forEach(track => track.stop());

                    let filenameForServer = "recording." + (finalMimeType.split('/')[1].split(';')[0] || "webm"); // e.g. recording.webm or recording.wav

                    statusDisplay.textContent = `Recording stopped. Sending ${filenameForServer} for recognition...`;
                    setControlsState(true); // Keep controls disabled during send
                    sendAudioForRecognition(recordedAudioBlob, filenameForServer);
                };

                mediaRecorder.onerror = (event) => {
                    console.error('MediaRecorder error:', event.error);
                    statusDisplay.textContent = 'Recording error: ' + event.error.name;
                    stream.getTracks().forEach(track => track.stop());
                    setControlsState(false);
                };

                mediaRecorder.start();
                statusDisplay.textContent = 'Recording... Click "Stop Recording" to finish.';
                setControlsState(true);
                stopButton.disabled = false; // Specifically enable stop
                recognizedTextArea.value = "";
                comparisonResultDisplay.innerHTML = ""; // Clear previous comparison
                lastProcessedFilenameForComparison = null; // Reset for new recording
                compareButton.disabled = true; // Disable until new recognition is successful
            } catch (err) {
                console.error('Error accessing microphone:', err);
                statusDisplay.textContent = 'Error accessing microphone: ' + err.message;
                alert('Could not access microphone: ' + err.message + '\nPlease ensure permissions are granted.');
                setControlsState(false);
            }
        }
    });

    stopButton.addEventListener('click', () => {
        if (mediaRecorder && mediaRecorder.state === 'recording') {
            mediaRecorder.stop();
            // onstop will handle UI and data sending
        }
    });

    // --- Upload Logic ---
    uploadButton.addEventListener('click', () => {
        const file = audioFileInput.files[0];
        if (file) {
            const allowedExtensions = [".wav", ".flac", ".ogg"];
            let isValidExtension = allowedExtensions.some(ext => file.name.toLowerCase().endsWith(ext));
            if (isValidExtension) {
                statusDisplay.textContent = `File selected: ${file.name}. Uploading for recognition...`;
                recognizedTextArea.value = "";
                comparisonResultDisplay.innerHTML = ""; // Clear previous comparison
                lastProcessedFilenameForComparison = null; // Reset for new upload
                compareButton.disabled = true; // Disable until new recognition is successful
                sendAudioForRecognition(file, file.name);
            } else {
                statusDisplay.textContent = 'Please upload a WAV, FLAC, or OGG file.';
                alert('Unsupported file type. Please upload a WAV, FLAC, or OGG file.');
                audioFileInput.value = '';
            }
        } else {
            statusDisplay.textContent = 'No file selected for upload.';
            alert('Please select an audio file to upload.');
        }
    });

    // --- API Interaction: Speech Recognition ---
    async function sendAudioForRecognition(audioBlobOrFile, clientSideFilename) {
        if (!audioBlobOrFile) {
            statusDisplay.textContent = 'No audio data to send.';
            setControlsState(false);
            return;
        }
        statusDisplay.textContent = 'Processing audio for recognition...';
        recognizedTextArea.value = '';
        setControlsState(true);

        const formData = new FormData();
        // The third argument to append is the filename that the server will see.
        formData.append('audio_file', audioBlobOrFile, clientSideFilename);
        formData.append('language', languageSelect.value);

        try {
            const response = await fetch('/recognize', { method: 'POST', body: formData });
            const result = await response.json();

            if (response.ok && result.success) {
                recognizedTextArea.value = result.text;
                statusDisplay.textContent = 'Recognition complete.';
                if (result.filename) { // Backend returns the filename it saved
                    lastProcessedFilenameForComparison = result.filename;
                    console.log("Set lastProcessedFilenameForComparison to:", lastProcessedFilenameForComparison);
                } else {
                     // This case should ideally not happen if backend always returns filename on success
                    lastProcessedFilenameForComparison = clientSideFilename; // Fallback, might not be exactly what server used if secure_filename changed it significantly
                    console.warn("Backend did not return a filename for recognized audio. Using client-side name as fallback for comparison:", lastProcessedFilenameForComparison);
                }
                fetchFileList(); // Refresh file list as new file was saved by backend
            } else {
                recognizedTextArea.value = "Recognition Error: " + (result.error || "Unknown server error.");
                statusDisplay.textContent = 'Recognition failed: ' + (result.error || "Unknown error");
                lastProcessedFilenameForComparison = null; // Clear if recognition failed
            }
        } catch (error) {
            console.error('Error during recognition API call:', error);
            recognizedTextArea.value = 'Network Error: Could not connect or server issue during recognition.';
            statusDisplay.textContent = 'Recognition failed (Network/Server Error).';
            lastProcessedFilenameForComparison = null; // Clear on network error
        } finally {
             setControlsState(false); // This will re-evaluate compareButton's state
        }
    }

    // --- Training File List Logic ---
    async function fetchFileList() {
        statusDisplay.textContent = 'Fetching file list...';
        // Do not disable all controls here, allow other operations if needed
        // setControlsState(true);

        try {
            const response = await fetch('/list_recordings');
            const result = await response.json();
            if (response.ok && result.success) {
                fileListSelect.innerHTML = '';
                if (result.files && result.files.length > 0) {
                    result.files.forEach(filename => {
                        const option = new Option(filename, filename);
                        fileListSelect.add(option);
                    });
                    if (statusDisplay.textContent === 'Fetching file list...') { // Avoid overwriting more important status
                       statusDisplay.textContent = 'File list updated. Select files for training.';
                    }
                } else {
                    fileListSelect.add(new Option("No recordings found on server.", ""));
                     if (statusDisplay.textContent === 'Fetching file list...') {
                        statusDisplay.textContent = 'No recordings found on server.';
                     }
                }
            } else {
                statusDisplay.textContent = 'Error fetching file list: ' + (result.error || 'Unknown server error');
            }
        } catch (error) {
            console.error('Error fetching file list:', error);
            statusDisplay.textContent = 'Error fetching file list (network issue).';
        } finally {
            // setControlsState(false); // Re-enable controls after fetch
        }
    }

    refreshFilesButton.addEventListener('click', fetchFileList);
    fetchFileList();

    // --- Training Logic ---
    trainButton.addEventListener('click', async () => {
        const selectedOptions = Array.from(fileListSelect.selectedOptions).map(option => option.value);
        if (selectedOptions.length === 0 || (selectedOptions.length === 1 && selectedOptions[0] === "")) {
            alert('Please select at least one valid file from the list to train.');
            statusDisplay.textContent = 'Training aborted: No valid files selected.';
            return;
        }

        statusDisplay.textContent = `Training started with ${selectedOptions.length} selected file(s)...`;
        setControlsState(true);
        comparisonResultDisplay.innerHTML = ""; // Clear previous comparison

        try {
            const response = await fetch('/train', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filenames: selectedOptions }),
            });
            const result = await response.json();
            if (response.ok && result.success) {
                statusDisplay.textContent = result.message || 'Training complete. Profile updated.';
                alert(result.message || 'Training complete. Profile updated.');
            } else {
                statusDisplay.textContent = 'Training failed: ' + (result.error || 'Unknown server error');
                alert('Training failed: ' + (result.error || 'Check server logs for details.'));
            }
        } catch (error) {
            console.error('Error during training API call:', error);
            statusDisplay.textContent = 'Training failed (network or server error).';
            alert('Training failed due to a network or server error.');
        } finally {
            setControlsState(false);
        }
    });

    // --- Comparison Logic ---
    compareButton.addEventListener('click', async () => {
        if (!lastProcessedFilenameForComparison) {
            alert('Please record or upload and successfully recognize an audio file first before comparing.');
            statusDisplay.textContent = 'Comparison aborted: No recently processed audio file to compare.';
            return;
        }

        statusDisplay.textContent = `Comparing ${lastProcessedFilenameForComparison} against target profile...`;
        comparisonResultDisplay.innerHTML = 'Comparing...';
        setControlsState(true);

        try {
            const response = await fetch('/compare', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filename: lastProcessedFilenameForComparison }),
            });
            const result = await response.json();

            if (response.ok && result.success) {
                comparisonResultDisplay.innerHTML =
                    `<h4>Comparison Results:</h4>
                     <p><strong>File:</strong> ${result.filename_compared}</p>
                     <p><strong>Euclidean Distance:</strong> ${result.distance.toFixed(4)} (lower is more similar)</p>
                     <p><strong>Similarity Score:</strong> ${result.similarity_score.toFixed(4)} (closer to 1.0 is more similar)</p>`;
                statusDisplay.textContent = 'Comparison complete.';
            } else {
                comparisonResultDisplay.innerHTML = `<p style="color: red;">Comparison failed: ${result.error || 'Unknown server error'}</p>`;
                statusDisplay.textContent = 'Comparison failed: ' + (result.error || 'Unknown server error');
            }
        } catch (error) {
            console.error('Error during comparison API call:', error);
            comparisonResultDisplay.innerHTML = `<p style="color: red;">Comparison failed (network or server error).</p>`;
            statusDisplay.textContent = 'Comparison failed (network/server error).';
        } finally {
            setControlsState(false);
            // compareButton remains enabled if lastProcessedFilenameForComparison is still valid
        }
    });
});
