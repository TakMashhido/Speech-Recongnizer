from flask import Flask, render_template, request, jsonify
import os
import json # Added for profile persistence
from werkzeug.utils import secure_filename
from voice_processing import recognize_speech_from_file, extract_features
import numpy as np

app = Flask(__name__)

UPLOAD_FOLDER = os.path.join(app.root_path, 'recordings')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Define path for the persisted voice profile
PROFILE_FILE = os.path.join(app.config['UPLOAD_FOLDER'], 'target_profile.json')

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    try:
        os.makedirs(app.config['UPLOAD_FOLDER'])
    except OSError as e:
        app.logger.error(f"Error creating upload folder {app.config['UPLOAD_FOLDER']}: {e}")

ALLOWED_EXTENSIONS = {'wav', 'flac', 'ogg'}

target_voice_profile = None # Global variable for trained profile (list of floats)

def load_existing_profile():
    """Loads the target voice profile from PROFILE_FILE if it exists."""
    global target_voice_profile
    if os.path.exists(PROFILE_FILE):
        try:
            with open(PROFILE_FILE, 'r') as f:
                loaded_profile = json.load(f)
                # Basic validation: check if it's a list of numbers (floats/ints)
                if isinstance(loaded_profile, list) and all(isinstance(x, (int, float)) for x in loaded_profile):
                    target_voice_profile = loaded_profile
                    app.logger.info(f"Target voice profile loaded from {PROFILE_FILE} with {len(target_voice_profile)} features.")
                else:
                    app.logger.warning(f"Profile file {PROFILE_FILE} content is not a valid list of numbers. Starting without a loaded profile.")
                    # Optionally, remove invalid file to prevent repeated load errors
                    # os.remove(PROFILE_FILE)
        except Exception as e:
            app.logger.error(f"Error loading target voice profile from {PROFILE_FILE}: {e}. Starting without a loaded profile.")
            # Optionally, attempt to remove corrupted file
            # try:
            #     if os.path.exists(PROFILE_FILE): os.remove(PROFILE_FILE)
            # except OSError as oe: app.logger.error(f"Error removing corrupted profile file: {oe}")
    else:
        app.logger.info(f"No existing profile file found at {PROFILE_FILE}. Target profile needs to be trained.")

# Load profile when the application starts
load_existing_profile()


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/recognize', methods=['POST'])
def recognize_audio_route():
    if 'audio_file' not in request.files:
        return jsonify({"success": False, "error": "No audio_file part in the request"}), 400

    file = request.files['audio_file']
    language = request.form.get('language', 'en-US')

    if file.filename == '':
        return jsonify({"success": False, "error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        filename_to_save = secure_filename(file.filename)
        temp_audio_path = os.path.join(app.config['UPLOAD_FOLDER'], filename_to_save)

        try:
            file.save(temp_audio_path)
            app.logger.info(f"Uploaded file saved to {temp_audio_path} for language {language}")
            recognition_result = recognize_speech_from_file(temp_audio_path, language)

            if recognition_result["success"]:
                return jsonify({"success": True, "text": recognition_result["text"], "filename": filename_to_save})
            else:
                return jsonify({"success": False, "error": recognition_result["error"], "filename": filename_to_save})
        except Exception as e:
            app.logger.error(f"Error processing file {filename_to_save}: {e}")
            if os.path.exists(temp_audio_path) and file.tell() == 0 :
                 try: os.remove(temp_audio_path)
                 except Exception as remove_e: app.logger.error(f"Error cleaning up empty file {temp_audio_path}: {remove_e}")
            return jsonify({"success": False, "error": f"Error processing file: {str(e)}"}), 500
    else:
        return jsonify({"success": False, "error": "File type not allowed or file not provided"}), 400

@app.route('/list_recordings', methods=['GET'])
def list_recordings_route():
    try:
        files = [f for f in os.listdir(app.config['UPLOAD_FOLDER'])
                 if f.lower().endswith(tuple(f".{ext}" for ext in ALLOWED_EXTENSIONS))]
        return jsonify({"success": True, "files": sorted(files)})
    except Exception as e:
        app.logger.error(f"Error listing recordings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/train', methods=['POST'])
def train_profile_route():
    global target_voice_profile
    try:
        data = request.get_json()
        if not data or 'filenames' not in data or not isinstance(data['filenames'], list):
            return jsonify({"success": False, "error": "Invalid request: 'filenames' list is required."}), 400

        selected_filenames = data['filenames']
        if not selected_filenames:
            return jsonify({"success": False, "error": "No files selected for training."}), 400

        all_features, processed_count, errors_encountered = [], 0, []
        for filename in selected_filenames:
            if os.path.sep in filename or '..' in filename:
                app.logger.warning(f"Skipping potentially unsafe filename: {filename}")
                errors_encountered.append(f"Skipped unsafe filename: {filename}")
                continue
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if not os.path.exists(file_path):
                app.logger.warning(f"Training: File not found: {file_path}")
                errors_encountered.append(f"File not found: {filename}")
                continue
            result = extract_features(file_path)
            if result.get("success"):
                all_features.append(result["features"])
                processed_count += 1
            else:
                error_msg = result.get("error", "Unknown error during feature extraction.")
                app.logger.warning(f"Feature extraction failed for {filename}: {error_msg}")
                errors_encountered.append(f"Failed for {filename}: {error_msg}")

        if not all_features:
            return jsonify({"success": False, "error": "Could not extract features from any selected file.","details": errors_encountered}), 400

        all_features_np = np.array(all_features, dtype=float) # Ensure float for calculation
        current_target_profile_list = np.mean(all_features_np, axis=0).tolist()

        # Persist the newly trained profile
        try:
            with open(PROFILE_FILE, 'w') as f:
                json.dump(current_target_profile_list, f)
            app.logger.info(f"Target voice profile saved to {PROFILE_FILE}")
            target_voice_profile = current_target_profile_list # Update in-memory profile
        except Exception as e:
            app.logger.error(f"Error saving target voice profile to {PROFILE_FILE}: {e}")
            # Continue to return success for training, but log this persistence error.
            # The in-memory profile is updated anyway for the current session.

        message = f"Training complete. Processed {processed_count} of {len(selected_filenames)} selected files. Profile updated."
        if errors_encountered: message += " Some files had issues: " + "; ".join(errors_encountered)
        return jsonify({"success": True, "message": message, "profile_dimensionality": len(target_voice_profile)})

    except ValueError as ve: # Catches errors from np.array conversion or np.mean if shapes mismatch
        app.logger.error(f"Error averaging features, possibly due to inconsistent feature vector shapes: {ve}")
        return jsonify({"success": False, "error": "Error averaging features. Ensure all processed files yield consistent feature vectors.", "details": str(ve)}), 500
    except Exception as e:
        app.logger.error(f"An error occurred during training: {e}")
        return jsonify({"success": False, "error": f"An unexpected error occurred during training: {str(e)}"}), 500

@app.route('/compare', methods=['POST'])
def compare_voice_route():
    global target_voice_profile
    if target_voice_profile is None: # Check the in-memory profile
        return jsonify({"success": False, "error": "No target voice profile trained or loaded. Please train first."}), 400

    data = request.get_json()
    if not data or 'filename' not in data:
        return jsonify({"success": False, "error": "Invalid request: 'filename' of an audio file is required."}), 400

    filename_to_compare = data['filename']
    if os.path.sep in filename_to_compare or '..' in filename_to_compare:
        app.logger.warning(f"Comparison rejected for invalid filename: {filename_to_compare}")
        return jsonify({"success": False, "error": "Invalid filename format."}), 400

    file_path_to_compare = os.path.join(app.config['UPLOAD_FOLDER'], filename_to_compare)
    if not os.path.exists(file_path_to_compare):
        return jsonify({"success": False, "error": f"File to compare not found on server: {filename_to_compare}"}), 404

    extraction_result = extract_features(file_path_to_compare)
    if not extraction_result.get("success"):
        return jsonify({"success": False, "error": f"Could not extract features from {filename_to_compare}: {extraction_result.get('error', 'Unknown extraction error')}"}), 500

    current_voice_features_np = np.array(extraction_result["features"], dtype=float)
    target_profile_np = np.array(target_voice_profile, dtype=float)

    if current_voice_features_np.shape != target_profile_np.shape:
        app.logger.error(f"Feature shape mismatch. Target: {target_profile_np.shape}, Current: {current_voice_features_np.shape}")
        return jsonify({"success": False, "error": f"Feature shape mismatch. Target: {target_profile_np.shape}, Current: {current_voice_features_np.shape}."}), 500

    distance = np.linalg.norm(target_profile_np - current_voice_features_np)
    similarity = 1 / (1 + distance)

    app.logger.info(f"Comparison for {filename_to_compare}: Distance={distance:.4f}, Similarity={similarity:.4f}")
    return jsonify({"success": True, "filename_compared": filename_to_compare, "distance": float(distance), "similarity_score": float(similarity)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
