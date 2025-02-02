import sys
import speech_recognition as sr
import google.generativeai as genai
import os
import datetime
import pyaudio
import wave
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QFileDialog, QTextEdit, QMessageBox, QHBoxLayout
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon

# Configure the Google Generative AI API
genai.configure(api_key="AIzaSyDkXR3W6SobrZd5rdT2ZwEFBT5hjmo8RYE")

class AudioRecorder(QThread):
    recording_complete = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.is_recording = False
        self.timestamp = datetime.datetime.now()
        self.output_file = f"recorded_audio_{self.timestamp.strftime('%Y-%m-%d_%H-%M-%S')}.wav"
        self.chunk = 1024
        self.sample_format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.frames = []
    
    def run(self):
        p = pyaudio.PyAudio()
        self.stream = p.open(format=self.sample_format, channels=self.channels, rate=self.rate, input=True, frames_per_buffer=self.chunk)
        self.is_recording = True

        while self.is_recording:
            data = self.stream.read(self.chunk)
            self.frames.append(data)
        
        self.stream.stop_stream()
        self.stream.close()
        p.terminate()
        
        wf = wave.open(self.output_file, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(p.get_sample_size(self.sample_format))
        wf.setframerate(self.rate)
        wf.writeframes(b''.join(self.frames))
        wf.close()
        
        self.recording_complete.emit(self.output_file)
    
    def stop(self):
        self.is_recording = False

class AudioTranscriber(QWidget):
    def save_transcript(self):
        transcript = self.text_area.toPlainText()
        if not transcript.strip():
            QMessageBox.warning(self, "Save Error", "There is no transcript to save.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Save Transcript", "", "Text Files (*.txt)")
        if file_path:
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(transcript)
            QMessageBox.information(self, "Success", "Transcript saved successfully!")

    def __init__(self):
        super().__init__()
        self.initUI()
        self.recognizer = sr.Recognizer()
        self.audio_file_path = ""
        self.timestamp = None
        self.recorder = AudioRecorder()
        self.recorder.recording_complete.connect(self.handle_recording_complete)
    
    def initUI(self):
        self.setWindowTitle("Note Ninja")
        self.setGeometry(200, 200, 600, 500)

        # Set the window icon
        self.setWindowIcon(QIcon("icon.png"))  # Ensure "icon.png" exists in the same directory

        self.layout = QVBoxLayout()
        
        self.label = QLabel("Select or Record an Audio File to Transcribe")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.label)
        
        self.record_btn = QPushButton("Start Recording")
        self.record_btn.clicked.connect(self.start_recording)
        self.layout.addWidget(self.record_btn)

        self.stop_record_btn = QPushButton("Stop Recording")
        self.stop_record_btn.setEnabled(False)
        self.stop_record_btn.clicked.connect(self.stop_recording)
        self.layout.addWidget(self.stop_record_btn)

        self.transcribe_btn = QPushButton("Select Audio File")
        self.transcribe_btn.clicked.connect(self.load_audio)
        self.layout.addWidget(self.transcribe_btn)
        
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.layout.addWidget(self.text_area)
        
        button_layout = QHBoxLayout()

        self.summarize_btn = QPushButton("Generate Meeting Minutes")
        self.summarize_btn.clicked.connect(self.summarize_text)
        button_layout.addWidget(self.summarize_btn)
        
        self.brief_summarize_btn = QPushButton("Summarize Paragraph")
        self.brief_summarize_btn.clicked.connect(self.summarize_paragraph)
        button_layout.addWidget(self.brief_summarize_btn)
        
        self.layout.addLayout(button_layout)
        
        self.save_btn = QPushButton("Save Transcript")
        self.save_btn.clicked.connect(self.save_transcript)
        self.layout.addWidget(self.save_btn)
        
        self.setLayout(self.layout)
    
    def start_recording(self):
        self.recorder = AudioRecorder()
        self.recorder.recording_complete.connect(self.handle_recording_complete)
        self.recorder.start()
        self.record_btn.setEnabled(False)
        self.stop_record_btn.setEnabled(True)
        self.timestamp = self.recorder.timestamp
        QMessageBox.information(self, "Recording", "Recording started. Click 'Stop Recording' to end.")
    
    def stop_recording(self):
        self.recorder.stop()
        self.stop_record_btn.setEnabled(False)
        self.record_btn.setEnabled(True)
    
    def handle_recording_complete(self, file_path):
        self.audio_file_path = file_path
        QMessageBox.information(self, "Recording Complete", "Recording finished. Processing...")
        self.transcribe_audio(file_path)
    
    def load_audio(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Audio File", "", "Audio Files (*.wav *.flac *.aiff *.opus)")
        if file_path:
            self.audio_file_path = file_path
            self.timestamp = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
            self.label.setText(f"Processing: {file_path}")
            self.transcribe_audio(file_path)
    
    def transcribe_audio(self, file_path):
        try:
            with sr.AudioFile(file_path) as source:
                audio = self.recognizer.record(source)
            transcript = self.recognizer.recognize_google(audio)
            formatted_time = self.timestamp.strftime('%Y-%m-%d %H:%M:%S') if self.timestamp else "Unknown"
            self.text_area.setText(f"Meeting Date & Time: {formatted_time}\n\n{transcript}")
        except sr.UnknownValueError:
            self.text_area.setText("Could not understand the audio.")
        except sr.RequestError:
            self.text_area.setText("Error connecting to the speech recognition service.")
    
    def summarize_text(self):
        transcript = self.text_area.toPlainText()
        if not transcript:
            return
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(f"Generate meeting minutes from this transcript:\n{transcript}")
        self.text_area.setText(f"Meeting Minutes:\n{response.text}\n\nFull Transcript:\n{transcript}")
    
    def summarize_paragraph(self):
        paragraph = self.text_area.toPlainText()
        if not paragraph:
            return
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(f"Summarize this paragraph briefly:\n{paragraph}")
        self.text_area.setText(f"Brief Summary:\n{response.text}\n\nOriginal Text:\n{paragraph}")

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Set the application-wide taskbar icon
    app.setWindowIcon(QIcon("icon.ico"))  # Ensure "icon.png" exists in the same directory

    window = AudioTranscriber()
    window.show()
    sys.exit(app.exec())