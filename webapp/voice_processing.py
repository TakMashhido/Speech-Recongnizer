import speech_recognition as sr
import os
import librosa # Added
import numpy as np # Added

def recognize_speech_from_file(audio_path, language_code="en-US"):
    """
    Recognizes speech from an audio file using Google Speech Recognition.

    Args:
        audio_path (str): The path to the audio file.
        language_code (str): The language code for recognition (e.g., "en-US", "bn-IN", "hi-IN").

    Returns:
        dict: A dictionary containing the recognition result.
              {"success": True, "text": "recognized text"} on success.
              {"success": False, "error": "error message"} on failure.
    """
    if not os.path.exists(audio_path):
        return {"success": False, "error": f"Audio file not found at path: {audio_path}"}
    if os.path.getsize(audio_path) == 0:
        return {"success": False, "error": f"Audio file is empty: {audio_path}"}

    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(audio_path) as source:
            audio_data = recognizer.record(source)
        text = recognizer.recognize_google(audio_data, language=language_code)
        return {"success": True, "text": text}
    except sr.UnknownValueError:
        return {"success": False, "error": "Speech recognition could not understand audio"}
    except sr.RequestError as e:
        return {"success": False, "error": f"Could not request results from Google Speech Recognition service; {e}"}
    except Exception as e:
        return {"success": False, "error": f"An unexpected error occurred during speech recognition: {e}"}

def extract_features(audio_path, n_mfcc=13):
    """
    Extracts MFCC features from an audio file.

    Args:
        audio_path (str): The path to the audio file.
        n_mfcc (int): The number of MFCCs to extract.

    Returns:
        dict: A dictionary containing the features or an error message.
              {"success": True, "features": [list of features]} on success.
              {"success": False, "error": "error message"} on failure.
    """
    if not os.path.exists(audio_path):
        return {"success": False, "error": f"Audio file not found for feature extraction: {audio_path}"}
    if os.path.getsize(audio_path) == 0:
        return {"success": False, "error": f"Audio file is empty, cannot extract features: {audio_path}"}

    try:
        y, sr = librosa.load(audio_path, sr=None) # sr=None to preserve original sample rate
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)
        mean_mfccs = np.mean(mfccs.T, axis=0)
        return {"success": True, "features": mean_mfccs.tolist()} # Convert numpy array to list for JSON
    except Exception as e:
        print(f"Error extracting features from {audio_path}: {e}") # Print to server log for debugging
        return {"success": False, "error": f"Feature extraction failed: {str(e)}"}


# Example usage (for testing this module directly)
if __name__ == '__main__':
    # This part would only run if you execute "python webapp/voice_processing.py"
    if not os.path.exists("dummy_test.wav"):
        import wave
        sample_rate = 44100; duration = 1; frequency = 440
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        tone = 0.5 * np.sin(2 * np.pi * frequency * t)
        audio_data_np = (tone * 32767).astype(np.int16)
        try:
            with wave.open("dummy_test.wav", "w") as wf:
                wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sample_rate)
                wf.writeframes(audio_data_np.tobytes())
            print("Created dummy_test.wav for testing voice_processing.py")
        except Exception as e:
            print(f"Could not create dummy_test.wav: {e}")

    if os.path.exists("dummy_test.wav"):
        print("\nTesting recognize_speech_from_file...")
        rec_result = recognize_speech_from_file("dummy_test.wav", "en-US")
        print(f"Recognition Result (dummy_test.wav): {rec_result}")
        if rec_result["success"] and rec_result["text"] == "":
            print("Note: Recognition successful but returned empty text (expected for simple tone/silence).")

        print("\nTesting extract_features...")
        feat_result = extract_features("dummy_test.wav")
        if feat_result["success"]:
            print(f"Feature Extraction Result (dummy_test.wav): {len(feat_result['features'])} MFCCs extracted (mean values).")
        else:
            print(f"Feature Extraction Failed: {feat_result['error']}")

        # Clean up dummy file
        # os.remove("dummy_test.wav")
        # print("\nCleaned up dummy_test.wav")
    else:
        print("dummy_test.wav was not created, skipping tests.")
