import sys
import os
import re
import webbrowser
import json
import shutil
import platform
import subprocess
import logging
import urllib.request
import zipfile
import tarfile
from PyQt5 import QtCore, QtGui, QtWidgets
from yt_dlp import YoutubeDL, utils

# Configure logging
logging.basicConfig(level=logging.INFO, filename='downloader.log',
                    format='%(asctime)s - %(levelname)s - %(message)s')


def is_ffmpeg_installed():
    """Check if FFmpeg is already installed and accessible."""
    return shutil.which("ffmpeg") is not None


def download_and_install_ffmpeg():
    """
    Automatically download and install FFmpeg temporarily by adding it to the current session's PATH.

    Returns:
        bool: True if installation was successful, False otherwise.
    """
    system = platform.system().lower()
    ffmpeg_url = ""
    extract_dir = os.path.join(os.getcwd(), "ffmpeg_temp")

    if system == "windows":
        ffmpeg_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    elif system == "linux":
        ffmpeg_url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
    elif system == "darwin":  # macOS
        ffmpeg_url = "https://evermeet.cx/ffmpeg/ffmpeg.zip"
    else:
        logging.error("Unsupported operating system for FFmpeg installation.")
        print("Unsupported operating system for FFmpeg installation.")  # Inform the user.
        return False # Added Return

    # Create a temporary directory for FFmpeg
    if not os.path.exists(extract_dir):
        os.makedirs(extract_dir)

    ffmpeg_archive = os.path.join(extract_dir, "ffmpeg_download")

    try:
        # Download FFmpeg
        print(f"Downloading FFmpeg from {ffmpeg_url}...")
        logging.info(f"Downloading FFmpeg from {ffmpeg_url}")
        try:
            urllib.request.urlretrieve(ffmpeg_url, ffmpeg_archive)
        except urllib.error.URLError as e:
            print(f"Error downloading FFmpeg: {e}")
            logging.error(f"Error downloading FFmpeg: {e}")
            return False
        print("Download complete.")
        logging.info(f"Downloaded FFmpeg from {ffmpeg_url} to {ffmpeg_archive}")

        # Extract the archive
        print("Extracting FFmpeg...")
        logging.info("Extracting FFmpeg archive")
        try:
            if ffmpeg_url.endswith(".zip"):
                with zipfile.ZipFile(ffmpeg_archive, "r") as zip_ref:
                    zip_ref.extractall(extract_dir)
            elif ffmpeg_url.endswith(".tar.xz"):
                with tarfile.open(ffmpeg_archive, "r:xz") as tar_ref:
                    tar_ref.extractall(extract_dir)
            else:
              logging.error(f"Unsupported archive format: {ffmpeg_url}")
              print(f"Unsupported archive format: {ffmpeg_url}")
              return False
        except Exception as e:
            print(f"Error extracting FFmpeg archive: {e}")
            logging.error(f"Error extracting FFmpeg archive: {e}")
            return False
        print("Extraction complete.")
        logging.info(f"Extracted FFmpeg archive to {extract_dir}")

        # Locate the ffmpeg executable
        print("Locating FFmpeg executable...")
        logging.info("Locating FFmpeg executable")
        ffmpeg_path = None
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file == "ffmpeg" or file == "ffmpeg.exe":
                    ffmpeg_path = os.path.join(root, file)
                    break
            if ffmpeg_path:
                break

        if not ffmpeg_path:
            print("Failed to locate FFmpeg executable after extraction.")
            logging.error("Failed to locate FFmpeg executable after extraction.")
            return False

        ffmpeg_dir = os.path.dirname(ffmpeg_path)

        # Temporary Installation: Add FFmpeg to the current session's PATH
        os.environ["PATH"] += os.pathsep + ffmpeg_dir
        print(f"FFmpeg has been installed temporarily and added to the current session's PATH.")
        logging.info("FFmpeg added to PATH temporarily.")

        # Temporary Install: Keep the ffmpeg files.
        # Cleanup downloaded archive and extracted files
        # os.remove(ffmpeg_archive)
        # logging.info(f"Removed FFmpeg archive: {ffmpeg_archive}")

        # shutil.rmtree(extract_dir)
        # logging.info(f"Removed temporary extraction directory: {extract_dir}")

        print("Installation complete.")
        logging.info("FFmpeg installation complete.")
        return True

    except Exception as e:
        print(f"Failed to install FFmpeg: {e}")
        logging.error(f"Failed to install FFmpeg: {e}")
        return False


class GradientWidget(QtWidgets.QWidget):
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        # X-like dark gradient with blue accents
        gradient = QtGui.QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, QtGui.QColor("#14171A"))  # Dark background color
        gradient.setColorAt(1, QtGui.QColor("#1DA1F2"))  # X/Twitter blue
        painter.fillRect(self.rect(), gradient)


class YouTubeDownloader(QtWidgets.QMainWindow):
    SUPPORTED_PLATFORMS = {
        'youtube.com': 'YouTube',
        'youtu.be': 'YouTube',
        'twitter.com': 'X (Twitter)',
        'x.com': 'X (Twitter)',
        'fb.watch': 'Facebook',
        'facebook.com': 'Facebook',
        # Add more supported platforms here
    }

    QUALITY_OPTIONS = [
        "Best Available (Default)",
        "Best Video + Audio",
        "Best Video Only",
        "Best Audio Only",
        "720p",
        "1080p",
        "4K"
    ]

    FORMAT_OPTIONS = [
        "mp4",
        "mp3",
        "wav",
        "mov"
    ]

    HISTORY_FILE = "download_history.json"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Downloader - FREE")
        self.setGeometry(100, 100, 800, 580)
        self.setFixedSize(800, 580)

        # Set the gradient background
        self.gradient = GradientWidget()
        self.setCentralWidget(self.gradient)

        # Set up UI elements
        self.setup_ui()

        self.downloader = None
        self.thread = None
        self.worker = None

        # Load download history
        self.load_history()

        # Check and install FFmpeg if necessary
        self.check_ffmpeg()

    def check_ffmpeg(self):
        if not is_ffmpeg_installed():
            self.prompt_ffmpeg_installation()


    def setup_ui(self):
        # Common Styles
        label_style = "color: white;"
        input_style = """
            background-color: #1E2631;
            color: white;
            border: 2px solid #1DA1F2;
            border-radius: 5px;
            padding: 5px;
        """
        button_style = """
            background-color: #1DA1F2;
            color: white;
            border: none;
            border-radius: 5px;
            padding: 8px 20px;
        """
        cancel_button_style = """
            background-color: #FF4D4D;
            color: white;
            border: none;
            border-radius: 5px;
            padding: 8px 20px;
        """
        dropdown_style = """
            background-color: #1E2631;
            color: white;
            border: 2px solid #1DA1F2;
            border-radius: 5px;
            padding: 5px;
        """

        # Central layout
        main_layout = QtWidgets.QVBoxLayout(self.centralWidget())
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)

        # Title Label
        self.title_label = QtWidgets.QLabel("Video Downloader - FREE", self)
        self.title_label.setFont(QtGui.QFont("Segoe UI", 16, QtGui.QFont.Bold))
        self.title_label.setStyleSheet("color: white;")
        self.title_label.setAlignment(QtCore.Qt.AlignCenter)
        main_layout.addWidget(self.title_label)

        # Clickable '@LukeKabbash on X' Label
        self.clickable_label = QtWidgets.QLabel(self)
        self.clickable_label.setText(
            '<i><a href="https://x.com/lukekabbash" style="color: white; text-decoration: none;"><span style="border-bottom: 1px solid blue;">@LukeKabbash on X</span></a></i>'
        )
        self.clickable_label.setFont(QtGui.QFont("Segoe UI", 10, QtGui.QFont.StyleItalic))
        self.clickable_label.setStyleSheet("color: white;")
        self.clickable_label.setAlignment(QtCore.Qt.AlignRight)
        self.clickable_label.setTextFormat(QtCore.Qt.RichText)
        self.clickable_label.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        self.clickable_label.setOpenExternalLinks(True)
        main_layout.addWidget(self.clickable_label)
        
        # Form Layout
        form_layout = QtWidgets.QFormLayout()

        # URL Label and Input
        self.url_label = QtWidgets.QLabel("Video URL:", self)
        self.url_label.setFont(QtGui.QFont("Segoe UI", 12))
        self.url_label.setStyleSheet(label_style)
        self.url_input = QtWidgets.QLineEdit(self)
        self.url_input.setFont(QtGui.QFont("Segoe UI", 12))
        self.url_input.setStyleSheet(input_style)
        form_layout.addRow(self.url_label, self.url_input)

        # Directory Label, Display, and Browse Button
        self.dir_label = QtWidgets.QLabel("Save to:", self)
        self.dir_label.setFont(QtGui.QFont("Segoe UI", 12))
        self.dir_label.setStyleSheet(label_style)
        self.dir_display = QtWidgets.QLineEdit(self)
        self.dir_display.setFont(QtGui.QFont("Segoe UI", 12))
        self.dir_display.setStyleSheet(input_style)
        self.dir_display.setReadOnly(True)
        # Set default directory to system's Downloads folder
        self.default_download_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
        self.dir_display.setText(self.default_download_dir)
        
        # Ensure the default directory exists
        if not os.path.exists(self.default_download_dir):
            try:
                os.makedirs(self.default_download_dir)
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Directory Error",
                                               f"Failed to create default directory: {str(e)}")
                self.dir_display.setText("")
        
        self.browse_button = QtWidgets.QPushButton("Browse", self)
        self.browse_button.setFont(QtGui.QFont("Segoe UI", 12))
        self.browse_button.setStyleSheet(button_style)
        self.browse_button.clicked.connect(self.browse_directory)
        
        dir_hbox = QtWidgets.QHBoxLayout()
        dir_hbox.addWidget(self.dir_display)
        dir_hbox.addWidget(self.browse_button)
        form_layout.addRow(self.dir_label, dir_hbox)

        # Quality/Type Selection Label
        self.quality_type_label = QtWidgets.QLabel("Quality/Type:", self)
        self.quality_type_label.setFont(QtGui.QFont("Segoe UI", 12))
        self.quality_type_label.setStyleSheet(label_style)
        
        # Quality Dropdown
        self.quality_dropdown = QtWidgets.QComboBox(self)
        self.quality_dropdown.setFont(QtGui.QFont("Segoe UI", 12))
        self.quality_dropdown.setStyleSheet(dropdown_style)
        self.quality_dropdown.addItems(self.QUALITY_OPTIONS)

        # Export Format Dropdown
        self.format_dropdown = QtWidgets.QComboBox(self)
        self.format_dropdown.setFont(QtGui.QFont("Segoe UI", 12))
        self.format_dropdown.setStyleSheet(dropdown_style)
        self.format_dropdown.addItems(self.FORMAT_OPTIONS)
        self.format_dropdown.setCurrentText("mp4")
        self.format_dropdown.setToolTip("Select export format (.mp4 is default)")
        
        # Download and Cancel Buttons
        self.download_button = QtWidgets.QPushButton("Download", self)
        self.download_button.setFont(QtGui.QFont("Segoe UI", 12))
        self.download_button.setStyleSheet(button_style)
        self.download_button.clicked.connect(self.start_download)

        self.cancel_button = QtWidgets.QPushButton("Cancel", self)
        self.cancel_button.setFont(QtGui.QFont("Segoe UI", 12))
        self.cancel_button.setStyleSheet(cancel_button_style)
        self.cancel_button.clicked.connect(self.cancel_download)
        self.cancel_button.setEnabled(False)

        # Download Buttons Layout
        button_hbox = QtWidgets.QHBoxLayout()
        button_hbox.addWidget(self.quality_dropdown)
        button_hbox.addWidget(self.format_dropdown)
        button_hbox.addStretch()
        button_hbox.addWidget(self.download_button)
        button_hbox.addWidget(self.cancel_button)
        form_layout.addRow(self.quality_type_label, button_hbox)
        
        # Add the form layout to the main layout
        main_layout.addLayout(form_layout)

        # Progress Bar
        self.progress_bar = QtWidgets.QProgressBar(self)
        self.progress_bar.setGeometry(50, 230, 700, 30) # Revert progress bar size.
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1E2631;
                color: white;
                border: 2px solid #1DA1F2;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #1DA1F2;
                width: 20px;
            }
        """)
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        # Status Label
        self.status_label = QtWidgets.QLabel("Idle", self)
        self.status_label.setFont(QtGui.QFont("Segoe UI", 12))
        self.status_label.setStyleSheet("color: white;")
        main_layout.addWidget(self.status_label)

        # Supported Platforms Label
        self.supported_label = QtWidgets.QLabel("Supported Platforms: YouTube, X (Twitter), Facebook", self)
        self.supported_label.setFont(QtGui.QFont("Segoe UI", 10))
        self.supported_label.setStyleSheet("color: #1DA1F2;")
        main_layout.addWidget(self.supported_label)
        
        # History Area
        history_layout = QtWidgets.QVBoxLayout()
        
        # Download History Label
        self.history_label = QtWidgets.QLabel("Download History:", self)
        self.history_label.setFont(QtGui.QFont("Segoe UI", 12))
        self.history_label.setStyleSheet(label_style)
        history_layout.addWidget(self.history_label)
        
        # Delete Selected File Button
        self.delete_button = QtWidgets.QPushButton("Delete File", self)
        self.delete_button.setFont(QtGui.QFont("Segoe UI", 12))
        self.delete_button.setStyleSheet(cancel_button_style)
        self.delete_button.clicked.connect(self.delete_selected_file)
        self.delete_button.setFixedWidth(160)

        # History header
        history_header = QtWidgets.QHBoxLayout()
        history_header.addWidget(self.history_label)
        history_header.addStretch()  # Push delete button to the right
        history_header.addWidget(self.delete_button)
        history_layout.addLayout(history_header)

        # Download History List Widget
        self.history_list = QtWidgets.QListWidget(self)
        self.history_list.setFont(QtGui.QFont("Segoe UI", 10))
        self.history_list.setStyleSheet("""
            QListWidget {
                background-color: #1E2631;
                color: white;
                border: 2px solid #1DA1F2;
                border-radius: 5px;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #1DA1F2;
                color: black;
            }
        """)
        self.history_list.itemDoubleClicked.connect(self.open_file_location)
        history_layout.addWidget(self.history_list)
        
        # Add history layout to the main layout
        main_layout.addLayout(history_layout)


    def prompt_ffmpeg_installation(self):
        """Prompt the user to install FFmpeg temporarily. If declined, close the application."""
        msg_box = QtWidgets.QMessageBox(self)
        msg_box.setIcon(QtWidgets.QMessageBox.Warning)
        msg_box.setWindowTitle("FFmpeg Not Found")
        msg_box.setText("You need FFmpeg to run this program.")
        msg_box.setInformativeText("Install temporarily? (This is required to run)")
        msg_box.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        msg_box.setDefaultButton(QtWidgets.QMessageBox.Yes)
        response = msg_box.exec_()

        if response == QtWidgets.QMessageBox.Yes:
            success = download_and_install_ffmpeg()
            if success:
                QtWidgets.QMessageBox.information(
                    self, "FFmpeg Installed",
                    "FFmpeg has been installed temporarily and added to the current session's PATH."
                )
            else:
                QtWidgets.QMessageBox.critical(
                    self, "FFmpeg Installation Failed",
                    "Failed to install FFmpeg automatically. The application will now close."
                )
                sys.exit(1)
        else:
            QtWidgets.QMessageBox.critical(
                self, "FFmpeg Required",
                "FFmpeg is required to run this program. The application will now close."
            )
            sys.exit(1)

    def load_history(self):
        if os.path.exists(self.HISTORY_FILE):
            try:
                with open(self.HISTORY_FILE, 'r') as f:
                    history = json.load(f)
                    for filepath in history:
                        self.history_list.addItem(filepath)
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "History Load Error",
                                              f"Failed to load download history: {str(e)}")
                logging.error(f"Failed to load download history: {str(e)}")

    def save_history(self):
        history = [self.history_list.item(i).text() for i in range(self.history_list.count())]
        try:
            with open(self.HISTORY_FILE, 'w') as f:
                json.dump(history, f, indent=4)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "History Save Error",
                                          f"Failed to save download history: {str(e)}")
            logging.error(f"Failed to save download history: {str(e)}")

    def browse_directory(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Download Directory", self.default_download_dir)
        if directory:
            self.dir_display.setText(directory)

    def validate_url(self, url):
        # Simple regex to extract domain
        pattern = r'^(?:http[s]?://)?([^:/\s]+)'
        match = re.match(pattern, url)
        if match:
            domain = match.group(1).lower()
            for key in self.SUPPORTED_PLATFORMS:
                if key in domain:
                    return self.SUPPORTED_PLATFORMS[key]
        return None

    def get_format_option(self):
        selected_format = self.format_dropdown.currentText()
        if selected_format == 'mp3':
            return 'mp3'
        elif selected_format == 'wav':
            return 'wav'
        elif selected_format == 'mov':
            return 'mov'
        else:
            return 'mp4'

    def start_download(self):
        url = self.url_input.text().strip()
        directory = self.dir_display.text().strip()
        export_format = self.get_format_option()
        selected_quality = self.quality_dropdown.currentText()

        if not url:
            QtWidgets.QMessageBox.warning(self, "Input Error", "Please enter a video URL.")
            return
        if not directory:
            QtWidgets.QMessageBox.warning(self, "Input Error", "Please select a download directory.")
            return

        platform_name = self.validate_url(url)
        if not platform_name:
            QtWidgets.QMessageBox.warning(self, "Unsupported URL",
                                          "The provided URL is either unsupported or invalid.")
            return

        # Extract video info to determine expected filename
        try:
            ydl_opts_info = {
                'quiet': True,
                'skip_download': True,
            }
            with YoutubeDL(ydl_opts_info) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get('title', 'downloaded_video')
                if export_format in ['mp3', 'wav']:
                    ext = export_format
                elif export_format == 'mov':
                    ext = 'mov'
                else:
                    ext = 'mp4'
                # Sanitize the title to create a valid filename
                filename = re.sub(r'[\\/*?:"<>|]', "", title)
                expected_filepath = os.path.join(directory, f"{filename}.{ext}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to retrieve video information: {str(e)}")
            logging.error(f"Failed to retrieve video information: {str(e)}")
            return

        # Check if the file already exists
        if os.path.exists(expected_filepath):
            response = QtWidgets.QMessageBox.question(
                self, "File Exists",
                f"The file '{os.path.basename(expected_filepath)}' already exists.\n"
                "Do you want to overwrite it?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            if response == QtWidgets.QMessageBox.No:
                QtWidgets.QMessageBox.information(self, "Download Skipped",
                                                  "The download has been skipped.")
                return
            else:
                try:
                    os.remove(expected_filepath)
                    logging.info(f"Existing file '{expected_filepath}' removed for overwrite.")
                except Exception as e:
                    QtWidgets.QMessageBox.critical(self, "Error",
                                                   f"Failed to remove existing file: {str(e)}")
                    logging.error(f"Failed to remove existing file '{expected_filepath}': {str(e)}")
                    return

        self.download_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.delete_button.setEnabled(False)  # Disable delete button during download
        self.status_label.setText(f"Starting download from {platform_name}...")
        self.progress_bar.setValue(0)

        # Configure yt-dlp options based on export format
        ydl_opts = {
            'outtmpl': os.path.join(directory, '%(title)s.%(ext)s'),
            'quiet': True,
            'noprogress': True,
            'ffmpeg_location': shutil.which("ffmpeg")  # Explicitly specify FFmpeg location
        }

        format_choice = self.get_format_option()
        if format_choice == 'mp3':
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        elif format_choice == 'wav':
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
                'preferredquality': '192',
            }]
        elif format_choice == 'mov':
            ydl_opts['format'] = 'bestvideo+bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mov',
            }]
        else:  # mp4
            ydl_opts['format'] = 'bestvideo+bestaudio/best'
            # No postprocessor needed for mp4

        # Run the download in a separate thread to keep UI responsive
        self.thread = QtCore.QThread()
        self.worker = DownloadWorker(YoutubeDL(ydl_opts), url, format_choice, expected_filepath)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.update_progress)
        self.worker.error.connect(self.handle_error)
        self.worker.finished.connect(self.download_finished)
        self.worker.download_complete.connect(self.add_to_history)
        self.thread.start()

    def cancel_download(self):
        if self.worker and self.worker.downloader:
            self.worker.downloader.process_interrupt()
            self.status_label.setText("Download canceled.")
            self.download_button.setEnabled(True)
            self.cancel_button.setEnabled(False)
            self.delete_button.setEnabled(True)  # Re-enable delete button after cancellation
            logging.info("Download canceled by user.")
            if self.thread:
                self.thread.quit()
                self.thread.wait()

    @QtCore.pyqtSlot(int)
    def update_progress(self, percent):
        self.progress_bar.setValue(percent)
        self.status_label.setText(f"Downloading... {percent}%")

    @QtCore.pyqtSlot(str)
    def handle_error(self, error_message):
        QtWidgets.QMessageBox.critical(self, "Download Error", error_message)
        self.status_label.setText("Download failed.")
        self.download_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.delete_button.setEnabled(True)  # Re-enable delete button after error
        logging.error(f"Download error: {error_message}")
        if self.thread:
            self.thread.quit()
            self.thread.wait()

    @QtCore.pyqtSlot(str)
    def add_to_history(self, filepath):
        # Add the downloaded file path to the history list
        self.history_list.addItem(filepath)
        self.save_history()
        logging.info(f"Download completed: {filepath}")
        self.download_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.delete_button.setEnabled(True)
        self.status_label.setText("Download finished.")

    def download_finished(self):
        self.status_label.setText("Download finished.")
        self.download_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.delete_button.setEnabled(True)
        logging.info("Download thread finished.")
        if self.thread:
            self.thread.quit()
            self.thread.wait()


    def open_file_location(self, item):
        filepath = item.text()
        if os.path.exists(filepath):
            folder = os.path.dirname(filepath)
            try:
                if platform.system() == "Windows":
                    os.startfile(folder)
                elif platform.system() == "Darwin":  # macOS
                    subprocess.call(["open", folder])
                else:  # Linux and others
                    subprocess.call(["xdg-open", folder])
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Open Folder Error",
                                              f"Could not open folder: {str(e)}")
                logging.error(f"Failed to open folder: {str(e)}")
        else:
            QtWidgets.QMessageBox.warning(self, "File Not Found",
                                          f"The file does not exist:\n{filepath}")
            logging.warning(f"File not found: {filepath}")

    def delete_selected_file(self):
        selected_items = self.history_list.selectedItems()
        if not selected_items:
            QtWidgets.QMessageBox.information(self, "No Selection", "Please select a file to delete.")
            return

        for item in selected_items:
            filepath = item.text()
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    logging.info(f"Deleted file: {filepath}")
                    self.history_list.takeItem(self.history_list.row(item))
                    self.save_history()
                except Exception as e:
                    QtWidgets.QMessageBox.critical(self, "Deletion Error",
                                                   f"Failed to delete '{os.path.basename(filepath)}': {str(e)}")
                    logging.error(f"Failed to delete '{filepath}': {str(e)}")
            else:
                QtWidgets.QMessageBox.warning(self, "File Not Found",
                                              f"The file does not exist:\n{filepath}")
                logging.warning(f"File not found for deletion: {filepath}")


class DownloadWorker(QtCore.QObject):
    progress = QtCore.pyqtSignal(int)
    error = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()
    download_complete = QtCore.pyqtSignal(str)  # Signal to emit filepath

    def __init__(self, downloader, url, format_choice, final_filepath):
        super().__init__()
        self.downloader = downloader
        self.url = url
        self.format_choice = format_choice
        self.final_filepath = final_filepath # Store expected filepath.

    def run(self):
        try:
            # Define a progress hook to emit signals
            def progress_hook(d):
                if d['status'] == 'downloading':
                    percent_str = d.get('_percent_str', '0.0%').strip('%')
                    try:
                        percent = int(float(percent_str))
                    except ValueError:
                        percent = 0
                    self.progress.emit(percent)
                elif d['status'] == 'finished':
                    # Instead of d.get('filepath') or d.get('filename'), we emit the final filepath
                    # We are now emitting the final file path, and not the raw video/audio files.
                    self.download_complete.emit(self.final_filepath)


            self.downloader.add_progress_hook(progress_hook)
            self.downloader.download([self.url])
        except utils.DownloadError as de:
            self.error.emit(f"Download failed: {str(de)}")
            logging.error(f"Download failed: {str(de)}")
        except Exception as e:
            self.error.emit(f"An unexpected error occurred: {str(e)}")
            logging.error(f"Unexpected error: {str(e)}")
        finally:
            # Ensure the thread is cleaned up in all cases
            self.finished.emit()

def main():
    # Initialize the application to handle FFmpeg installation prompts
    app = QtWidgets.QApplication(sys.argv)

    # Create the main application window
    downloader = YouTubeDownloader()
    downloader.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()