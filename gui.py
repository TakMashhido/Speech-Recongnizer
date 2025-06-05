import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
from tkinter import simpledialog
import speech_recognition as sr
import threading
import wave
import datetime
import os
import librosa
import numpy as np
from queue import Queue
import re # For sanitizing filename

class VoiceTrainingApp:
    def __init__(self, master):
        self.master = master
        master.title("Voice Training App")
        master.geometry("750x750") # Increased size for new UI elements

        # --- Initialize Core Components ---
        self.recognizer = sr.Recognizer()
        self.microphone_names = []

        # --- Application State Variables ---
        self.recordings_dir = "recordings"
        self.target_voice_features = None
        self.last_recorded_file = None
        self.dialog_result = None
        self.dialog_done_event = threading.Event()

        self.lang_map = { "English": "en-US", "Bengali": "bn-IN", "Hindi": "hi-IN" }

        self._create_recordings_directory()
        self._message_queue = Queue()
        self._process_message_queue()

        # --- UI Elements ---
        current_row = 0

        # Microphone Selection
        self.mic_label = ttk.Label(master, text="Select Microphone:")
        self.mic_label.grid(row=current_row, column=0, padx=10, pady=(10,5), sticky="w")
        self.mic_selected = tk.StringVar()
        self.mic_dropdown = ttk.Combobox(master, textvariable=self.mic_selected, state="readonly", width=45)
        self.mic_dropdown.grid(row=current_row, column=1, columnspan=2, padx=10, pady=(10,5), sticky="ew")
        current_row += 1

        # Language Selection
        self.lang_label = ttk.Label(master, text="Recognition Language:")
        self.lang_label.grid(row=current_row, column=0, padx=10, pady=5, sticky="w")
        self.lang_selected = tk.StringVar()
        self.lang_combobox = ttk.Combobox(master, textvariable=self.lang_selected,
                                          values=list(self.lang_map.keys()), state="readonly", width=45)
        self.lang_combobox.set("English")
        self.lang_combobox.grid(row=current_row, column=1, columnspan=2, padx=10, pady=5, sticky="ew")
        current_row += 1

        # Control Buttons
        self.button_frame = ttk.LabelFrame(master, text="Controls")
        self.button_frame.grid(row=current_row, column=0, columnspan=3, padx=10, pady=10, sticky="ew")
        current_row += 1

        self.record_button = ttk.Button(self.button_frame, text="Record", command=self.start_recording_thread)
        self.record_button.pack(side="left", padx=5, pady=5)
        self.stop_button = ttk.Button(self.button_frame, text="Stop", state=tk.DISABLED)
        self.stop_button.pack(side="left", padx=5, pady=5)
        self.train_button = ttk.Button(self.button_frame, text="Train Selected Files", command=self.start_training_thread) # Updated text
        self.train_button.pack(side="left", padx=5, pady=5)
        self.compare_button = ttk.Button(self.button_frame, text="Compare Voice", command=self.start_comparison_thread)
        self.compare_button.pack(side="left", padx=5, pady=5)

        # Training File Selection Area
        self.files_frame = ttk.LabelFrame(master, text="Select Recordings for Training")
        self.files_frame.grid(row=current_row, column=0, columnspan=3, padx=10, pady=10, sticky="ewns")
        current_row += 1

        self.training_files_listbox = tk.Listbox(self.files_frame, selectmode=tk.EXTENDED, height=6, exportselection=False)
        self.training_files_scrollbar = ttk.Scrollbar(self.files_frame, orient=tk.VERTICAL, command=self.training_files_listbox.yview)
        self.training_files_listbox.configure(yscrollcommand=self.training_files_scrollbar.set)

        self.training_files_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5,0), pady=5)
        self.training_files_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0,5), pady=5)

        self.refresh_files_button = ttk.Button(self.files_frame, text="Refresh File List", command=self._populate_training_files_listbox)
        self.refresh_files_button.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=(0,5))


        # Output/Message Area
        self.message_area_label = ttk.Label(master, text="Messages:")
        self.message_area_label.grid(row=current_row, column=0, padx=10, pady=(10,0), sticky="w")
        current_row += 1
        self.message_area = scrolledtext.ScrolledText(master, wrap=tk.WORD, height=10, width=80)
        self.message_area.grid(row=current_row, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")

        master.columnconfigure(1, weight=1)
        master.rowconfigure(current_row - 3, weight=0) # files_frame not expanding much
        master.rowconfigure(current_row, weight=1) # message_area row expands

        self.load_microphones()
        self._populate_training_files_listbox() # Initial population
        self._display_welcome_message()

    def _display_welcome_message(self):
        self._write_to_message_area("Welcome to the Voice Training App!")
        self._write_to_message_area("Instructions:")
        self._write_to_message_area("1. Select Microphone and Recognition Language.")
        self._write_to_message_area("2. Click 'Record'. You'll be prompted for a filename. Create multiple recordings.")
        self._write_to_message_area("3. In 'Select Recordings for Training', click 'Refresh File List'. Select the files you want to use.")
        self._write_to_message_area("4. Click 'Train Selected Files' to build a voice profile from them.")
        self._write_to_message_area("5. Record a new voice sample you want to compare.")
        self._write_to_message_area("6. Click 'Compare Voice' to see how similar it is to the trained profile.")
        self._write_to_message_area("---")

    def _populate_training_files_listbox(self):
        """Clears and repopulates the listbox with .wav files from the recordings directory."""
        self.training_files_listbox.delete(0, tk.END)
        if not os.path.exists(self.recordings_dir):
            self._write_to_message_area(f"Warning: Recordings directory '{self.recordings_dir}' not found. Cannot list files.")
            # Optionally, insert a message into the listbox itself
            # self.training_files_listbox.insert(tk.END, "Recordings directory not found.")
            return

        try:
            files = [f for f in os.listdir(self.recordings_dir) if f.endswith(".wav")]
            if not files:
                self.training_files_listbox.insert(tk.END, "No .wav files found in recordings directory.")
                self._write_to_message_area(f"Info: No .wav files found in '{self.recordings_dir}'.")
            else:
                for f_name in sorted(files): # Sort for consistent order
                    self.training_files_listbox.insert(tk.END, f_name)
                self._write_to_message_area(f"Info: Refreshed training file list. Found {len(files)} .wav files.")
        except Exception as e:
            self._write_to_message_area(f"Error listing recording files: {e}")
            self.training_files_listbox.insert(tk.END, "Error listing files.")


    def _create_recordings_directory(self): # (Content unchanged)
        if not os.path.exists(self.recordings_dir):
            try:
                os.makedirs(self.recordings_dir)
                self._write_to_message_area(f"Info: Created directory for recordings at '{os.path.abspath(self.recordings_dir)}'")
            except Exception as e:
                self._write_to_message_area(f"Error: Could not create recordings directory '{self.recordings_dir}': {e}")

    def _write_to_message_area(self, message): # (Content unchanged)
        self._message_queue.put(message)

    def _process_message_queue(self): # (Content unchanged)
        try:
            while not self._message_queue.empty():
                message = self._message_queue.get_nowait()
                self.message_area.config(state=tk.NORMAL)
                self.message_area.insert(tk.END, str(message) + "\n")
                self.message_area.see(tk.END)
                self.message_area.config(state=tk.DISABLED)
        except Exception:
            pass
        self.master.after(100, self._process_message_queue)

    def load_microphones(self): # (Content unchanged)
        self._write_to_message_area("Loading microphones...")
        try:
            self.microphone_names = sr.Microphone.list_microphone_names()
            if not self.microphone_names:
                self._write_to_message_area("Warning: No microphones found. Recording will be disabled.")
                self.record_button.config(state=tk.DISABLED)
                self.mic_dropdown.config(values=["No microphones found"])
                if list(self.mic_dropdown.cget('values')): self.mic_dropdown.current(0)
            else:
                self.mic_dropdown.config(values=self.microphone_names)
                common_mics = [m for m in self.microphone_names if any(keyword in m.lower() for keyword in ["default", "primary", "pulse", "headset", "usb"])]
                if common_mics: self.mic_dropdown.set(common_mics[0])
                elif self.microphone_names: self.mic_dropdown.current(0)
                self._write_to_message_area(f"Info: Microphones loaded. Found {len(self.microphone_names)} devices. Please select one.")
                self.record_button.config(state=tk.NORMAL)
        except Exception as e:
            self._write_to_message_area(f"Critical Error: Could not list microphones. Details: {e}")
            self.record_button.config(state=tk.DISABLED)
            self.mic_dropdown.config(values=["Error loading microphones"])
            if list(self.mic_dropdown.cget('values')): self.mic_dropdown.current(0)

    def _set_buttons_state(self, state): # (Content unchanged)
        for button in [self.record_button, self.train_button, self.compare_button]:
            button.config(state=state)

    def _ask_filename_dialog(self, suggestion, event_to_set): # (Content unchanged)
        custom_name = simpledialog.askstring("Input Filename",
                                             "Enter filename for recording (no extension, spaces will be replaced with '_'):",
                                             initialvalue=suggestion,
                                             parent=self.master)
        self.dialog_result = custom_name
        event_to_set.set()

    def start_recording_thread(self): # (Content unchanged, language passing logic already there)
        selected_mic_name = self.mic_selected.get()
        if not selected_mic_name or selected_mic_name in ["No microphones found", "Error loading microphones", "Error loading mics", ""]:
            self._write_to_message_area("Action Required: Please select a valid microphone before recording.")
            return
        selected_lang_display_name = self.lang_selected.get()
        if not selected_lang_display_name:
            self._write_to_message_area("Action Required: Please select a recognition language.")
            return
        try:
            device_idx = self.microphone_names.index(selected_mic_name)
        except (ValueError, AttributeError):
            self._write_to_message_area(f"Error: Could not find or initialize the selected microphone: {selected_mic_name}")
            return
        self._set_buttons_state(tk.DISABLED)
        self.recording_thread = threading.Thread(target=self.record_and_recognize,
                                                 args=(device_idx, selected_mic_name, selected_lang_display_name))
        self.recording_thread.daemon = True
        self.recording_thread.start()

    def record_and_recognize(self, device_index, mic_name, selected_lang_display_name): # (Content unchanged)
        self._write_to_message_area(f"Info: Starting recording with '{mic_name}' (Language: {selected_lang_display_name})...")
        audio_data = None
        try:
            with sr.Microphone(device_index=device_index) as source:
                self._write_to_message_area("Info: Adjusting for ambient noise (1 second)... Please wait.")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                self._write_to_message_area("Info: Ambient noise adjustment complete. Speak now (max 10 seconds).")
                audio_data = self.recognizer.listen(source, timeout=7, phrase_time_limit=10)
                self._write_to_message_area("Info: Audio capture complete. Processing...")
        except sr.WaitTimeoutError:
             self._write_to_message_area("Info: No speech detected within the timeout period (7 seconds).")
        except Exception as e:
            self._write_to_message_area(f"Error during recording with '{mic_name}': {e}")

        if audio_data:
            default_timestamp_stem = f"recording_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.dialog_result = None
            self.dialog_done_event.clear()
            self.master.after(0, self._ask_filename_dialog, default_timestamp_stem, self.dialog_done_event)

            if not self.dialog_done_event.wait(timeout=30.0):
                 self._write_to_message_area("Warning: Filename input dialog timed out. Using default name.")
                 custom_name = None
            else:
                 custom_name = self.dialog_result

            chosen_filename_stem = ""
            if custom_name and custom_name.strip():
                sanitized_name = custom_name.strip()
                sanitized_name = re.sub(r'\s+', '_', sanitized_name)
                sanitized_name = re.sub(r'[^\w\.-]', '_', sanitized_name)
                chosen_filename_stem = sanitized_name
            else:
                chosen_filename_stem = default_timestamp_stem
                self._write_to_message_area(f"Info: No custom name ('{custom_name}') provided or input was empty, using default: '{chosen_filename_stem}.wav'")

            final_filename = chosen_filename_stem + ".wav"
            save_path = os.path.join(self.recordings_dir, final_filename)

            try:
                with wave.open(save_path, 'wb') as wf:
                    wav_file_data = audio_data.get_wav_data()
                    wf.writeframes(wav_file_data)
                self._write_to_message_area(f"Success: Audio saved as '{save_path}'")
                self.last_recorded_file = save_path
            except Exception as e:
                self._write_to_message_area(f"Error saving audio to '{save_path}': {e}")
                self.last_recorded_file = None

            language_code = self.lang_map.get(selected_lang_display_name, "en-US")
            if selected_lang_display_name not in self.lang_map:
                 self._write_to_message_area(f"Warning: Selected language '{selected_lang_display_name}' not in map, defaulting to English (en-US).")

            self._write_to_message_area(f"Info: Recognizing speech (Language: {selected_lang_display_name} [{language_code}])...")
            try:
                recognized_text = self.recognizer.recognize_google(audio_data, language=language_code)
                self._write_to_message_area(f"Recognized Text: {recognized_text}")
            except sr.UnknownValueError:
                self._write_to_message_area("Info: Google Speech Recognition could not understand the audio.")
            except sr.RequestError as e:
                self._write_to_message_area(f"Warning: Could not request results from Google Speech Recognition service; {e}")
            except Exception as e:
                self._write_to_message_area(f"Error during speech recognition: {e}")

        self.master.after(0, lambda: self._set_buttons_state(tk.NORMAL))
        # Refresh file list after a recording is made and potentially saved
        self.master.after(10, self._populate_training_files_listbox)


    def start_training_thread(self):
        self._set_buttons_state(tk.DISABLED)
        self._write_to_message_area("Info: Training process started...")

        # Get selected files from Listbox in the main thread
        selected_indices = self.training_files_listbox.curselection()
        selected_files_for_training = [self.training_files_listbox.get(i) for i in selected_indices]

        if not selected_files_for_training:
            self._write_to_message_area("Action Required: Please select one or more .wav files from the list for training.")
            self._set_buttons_state(tk.NORMAL) # Re-enable buttons
            return

        self.training_thread = threading.Thread(target=self.train_model, args=(selected_files_for_training,))
        self.training_thread.daemon = True
        self.training_thread.start()

    def train_model(self, selected_files): # Argument: selected_files
        all_features_list = []
        processed_files_count = 0
        try:
            # recordings_dir check is implicitly done by file selection, but good to have if list was stale
            if not os.path.exists(self.recordings_dir):
                self._write_to_message_area(f"Error: Recordings directory '{self.recordings_dir}' not found.")
                return

            # The list of files to process is now 'selected_files' passed as argument
            self._write_to_message_area(f"Info: Starting training with {len(selected_files)} selected files.")

            for filename in selected_files: # Iterate over selected files
                filepath = os.path.join(self.recordings_dir, filename) # Construct full path
                if not os.path.exists(filepath):
                    self._write_to_message_area(f"Warning: File '{filename}' not found in recordings directory. Skipping.")
                    continue

                self._write_to_message_area(f"Info: Processing '{filename}' for training...")
                try:
                    y, sr_librosa = librosa.load(filepath, sr=None)
                    mfccs = librosa.feature.mfcc(y=y, sr=sr_librosa, n_mfcc=13)
                    mean_mfccs = np.mean(mfccs.T, axis=0)
                    all_features_list.append(mean_mfccs)
                    processed_files_count += 1
                except Exception as e:
                    self._write_to_message_area(f"Error processing file '{filename}' for training: {e}. Skipping this file.")

            if all_features_list:
                self.target_voice_features = np.mean(all_features_list, axis=0)
                self._write_to_message_area(f"Success: Training complete. Analyzed {processed_files_count} selected recordings.")
                self._write_to_message_area(f"Info: Average target voice features computed (shape: {self.target_voice_features.shape}).")
            elif processed_files_count == 0 and len(selected_files) > 0 : # Only if files were selected but none could be processed
                 self._write_to_message_area("Warning: Training attempted on selected files, but no features could be extracted.")
            # If selected_files was empty, it's handled in start_training_thread
        except Exception as e:
            self._write_to_message_area(f"Error during the training process: {e}")
        finally:
            self.master.after(0, lambda: self._set_buttons_state(tk.NORMAL))

    def start_comparison_thread(self): # (Content unchanged)
        self._set_buttons_state(tk.DISABLED)
        self._write_to_message_area("Info: Starting voice comparison...")
        self.comparison_thread = threading.Thread(target=self.compare_voice_features)
        self.comparison_thread.daemon = True
        self.comparison_thread.start()

    def compare_voice_features(self): # (Content unchanged)
        try:
            if self.target_voice_features is None:
                self._write_to_message_area("Action Required: Comparison failed. Please train the model first.")
                return
            if self.last_recorded_file is None or not os.path.exists(self.last_recorded_file):
                self._write_to_message_area("Action Required: Comparison failed. Please record your voice first.")
                return
            self._write_to_message_area(f"Info: Comparing with last recording: '{os.path.basename(self.last_recorded_file)}'")
            current_voice_features = None
            try:
                y, sr_librosa = librosa.load(self.last_recorded_file, sr=None)
                mfccs = librosa.feature.mfcc(y=y, sr=sr_librosa, n_mfcc=13)
                current_voice_features = np.mean(mfccs.T, axis=0)
            except Exception as e:
                self._write_to_message_area(f"Error processing current recording '{os.path.basename(self.last_recorded_file)}': {e}")
                return
            if current_voice_features is None:
                self._write_to_message_area("Error: Failed to extract features from the current recording.")
                return
            if self.target_voice_features.shape != current_voice_features.shape:
                self._write_to_message_area(f"Error: Comparison failed due to feature shapes mismatch.")
                return
            distance = np.linalg.norm(self.target_voice_features - current_voice_features)
            similarity = 1 / (1 + distance)
            self._write_to_message_area("\n--- Voice Comparison Results ---")
            self._write_to_message_area(f"File Compared: '{os.path.basename(self.last_recorded_file)}'")
            self._write_to_message_area(f"Euclidean Distance: {distance:.4f} (Lower is more similar)")
            self._write_to_message_area(f"Similarity Score: {similarity:.4f} (Closer to 1.0 is more similar)")
            self._write_to_message_area("-------------------------------\n")
        except Exception as e:
            self._write_to_message_area(f"Error during voice comparison: {e}")
        finally:
            self.master.after(0, lambda: self._set_buttons_state(tk.NORMAL))


if __name__ == "__main__":
    root = tk.Tk()
    app = VoiceTrainingApp(root)
    root.mainloop()
