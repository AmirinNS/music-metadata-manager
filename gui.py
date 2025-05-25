#!/usr/bin/env python3
import os
import sys
import csv
import re
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTableWidget, QTableWidgetItem, 
                            QPushButton, QVBoxLayout, QHBoxLayout, QFileDialog, 
                            QWidget, QLabel, QProgressBar, QMessageBox, QCheckBox,
                            QTabWidget, QSpinBox, QComboBox, QGroupBox, QFormLayout, QHeaderView)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import mutagen
from mutagen.mp3 import MP3, EasyMP3
from mutagen.id3 import ID3, TIT2, TPE1, TPE2, TALB, TRCK, TCON, TPOS
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from mutagen.oggvorbis import OggVorbis
from mutagen.asf import ASF

# Import the existing extraction and update functions
try:
    # Import from extract script
    from extract_music_metadata import (
        is_audio_file,
        extract_track_and_title_from_filename,
        extract_mp3_tags,
        extract_flac_tags,
        extract_m4a_tags,
        extract_ogg_tags,
        extract_wma_tags
    )
    
    # Import from update script
    from update_music_metadata import (
        rename_file_with_track_number,
        update_mp3_tags,
        update_flac_tags,
        update_m4a_tags,
        update_ogg_tags,
        update_wma_tags,
        update_tags_from_csv
    )
    
    print("Successfully imported functions from the scripts")
    
except ImportError as e:
    print(f"Error importing scripts: {e}")
    QMessageBox.critical(None, "Script Import Error", 
                        f"Could not import functions from scripts: {e}\n\n"
                        "Make sure the scripts are in the same directory as this application "
                        "and are named properly (with underscores instead of hyphens).")
    sys.exit(1)

def update_tags_from_csv_with_callback(csv_file, input_folder, dry_run=False, verbose=False, 
                                      recursive=False, rename_files=False, progress_callback=None):
    """
    Wrapper around the original update_tags_from_csv function that adds progress callback support
    """
    # This is a custom implementation that wraps the original function
    # and adds progress reporting for the GUI
    
    # Make sure input folder exists and normalize the path
    input_folder = os.path.normpath(os.path.expanduser(input_folder))
    if not os.path.isdir(input_folder):
        raise ValueError(f"Input folder does not exist: {input_folder}")
    
    # Keep track of statistics
    stats = {
        'total': 0,
        'updated': 0,
        'renamed': 0,
        'failed': 0,
        'skipped': 0,
        'not_found': 0
    }
    
    # First, build a dictionary of filenames from the input folder
    file_dict = {}
    if recursive:
        # Walk through all subdirectories
        for root, _, files in os.walk(input_folder):
            for file in files:
                if is_audio_file(file):
                    # Use a tuple of filename and parent directory as key to handle duplicates
                    parent_dir = os.path.basename(root)
                    file_dict[(file, parent_dir)] = os.path.join(root, file)
                    # Also store with just filename as key for backward compatibility
                    if file not in file_dict:
                        file_dict[file] = os.path.join(root, file)
    else:
        # Just look in the specified directory
        for file in os.listdir(input_folder):
            filepath = os.path.join(input_folder, file)
            if is_audio_file(file) and os.path.isfile(filepath):
                file_dict[file] = filepath
    
    if verbose:
        print(f"Found {len(file_dict)} audio files in the input folder")
    
    # Read the CSV file
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        # Check that required columns exist
        required_columns = ['filename']
        if reader.fieldnames is None:
            raise ValueError("CSV file appears to be empty or improperly formatted")
            
        missing_columns = [col for col in required_columns if col not in reader.fieldnames]
        if missing_columns:
            raise ValueError(f"CSV is missing required columns: {', '.join(missing_columns)}")
        
        # Get available tag columns from CSV header
        supported_tags = ['album', 'album_artist', 'artist', 'genre', 'title', 
                         'track_number', 'disc_number', 'composer', 'year', 'comment']
        available_tags = [col for col in reader.fieldnames if col in supported_tags]
        
        if verbose:
            print(f"Found tag columns in CSV: {', '.join(available_tags)}")
        
        # Process each row
        rows = list(reader)  # Convert to list for progress tracking
        
        for i, row in enumerate(rows):
            stats['total'] += 1
            
            # Get the filename
            filename = row.get('filename', '').strip()
            if not filename:
                message = "Skipping row with empty filename"
                if progress_callback:
                    progress_callback(filename, "Skipped", message)
                stats['skipped'] += 1
                continue
            
            # Try to find the file
            filepath = None
            
            # Check if we have a direct match
            if filename in file_dict:
                filepath = file_dict[filename]
            else:
                # Try to match with parent directory if available
                parent_dir = row.get('parent_dir', '')
                if parent_dir and (filename, parent_dir) in file_dict:
                    filepath = file_dict[(filename, parent_dir)]
                else:
                    # Last resort: try case-insensitive matching
                    for key in file_dict:
                        if isinstance(key, str) and key.lower() == filename.lower():
                            filepath = file_dict[key]
                            break
            
            if filepath is None:
                message = f"File not found"
                if progress_callback:
                    progress_callback(filename, "Not Found", message)
                stats['not_found'] += 1
                continue
            
            # Skip rows with empty data for all tag columns
            if all(not row.get(col, '') for col in available_tags):
                message = "No tag data provided"
                if progress_callback:
                    progress_callback(filename, "Skipped", message)
                stats['skipped'] += 1
                continue
            
            try:
                # Determine file type and update tags accordingly
                if filepath.lower().endswith('.mp3'):
                    update_mp3_tags(filepath, row, available_tags, dry_run, verbose)
                elif filepath.lower().endswith('.flac'):
                    update_flac_tags(filepath, row, available_tags, dry_run, verbose)
                elif filepath.lower().endswith('.m4a'):
                    update_m4a_tags(filepath, row, available_tags, dry_run, verbose)
                elif filepath.lower().endswith('.ogg'):
                    update_ogg_tags(filepath, row, available_tags, dry_run, verbose)
                elif filepath.lower().endswith('.wma'):
                    update_wma_tags(filepath, row, available_tags, dry_run, verbose)
                else:
                    message = f"Unsupported file type"
                    if progress_callback:
                        progress_callback(filename, "Skipped", message)
                    stats['skipped'] += 1
                    continue
                
                stats['updated'] += 1
                message = "Tags updated"
                
                # Check if we need to rename the file to include track number and/or disc number
                if rename_files and 'track_number' in available_tags and row.get('track_number'):
                    # Get disc number if available
                    disc_number = row.get('disc_number') if 'disc_number' in available_tags else None
                    
                    # Rename the file to include track number and disc number if needed
                    new_filepath = rename_file_with_track_number(
                        filepath, 
                        row['track_number'], 
                        dry_run, 
                        verbose, 
                        disc_number
                    )
                    
                    if new_filepath != filepath:
                        stats['renamed'] += 1
                        message += ", file renamed"
                        filepath = new_filepath
                
                if progress_callback:
                    progress_callback(filename, "Updated", message)
                
            except Exception as e:
                stats['failed'] += 1
                message = f"Error: {str(e)}"
                if progress_callback:
                    progress_callback(filename, "Failed", message)
    
    return stats    

class MusicMetadataManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Music Metadata Manager")
        self.setGeometry(100, 100, 1200, 800)
        
        # Initialize variables
        self.music_files = []
        self.metadata = []
        self.current_folder = os.path.expanduser("~")
        self.csv_path = None
        
        # Create UI
        self.setup_ui()
        
    def setup_ui(self):
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        
        # Create tabs
        tabs = QTabWidget()
        extract_tab = QWidget()
        edit_tab = QWidget()
        update_tab = QWidget()
        
        tabs.addTab(extract_tab, "Extract Metadata")
        tabs.addTab(edit_tab, "Edit Metadata")
        tabs.addTab(update_tab, "Update Files")
        
        # Setup each tab
        self.setup_extract_tab(extract_tab)
        self.setup_edit_tab(edit_tab)
        self.setup_update_tab(update_tab)
        
        main_layout.addWidget(tabs)
        self.setCentralWidget(main_widget)
    
    def setup_extract_tab(self, tab):
        layout = QVBoxLayout(tab)
        
        # Top controls
        top_controls = QHBoxLayout()
        
        # Folder selection
        folder_btn = QPushButton("Select Music Folder")
        folder_btn.clicked.connect(self.select_folder)
        self.folder_label = QLabel("No folder selected")
        
        # Options
        options_group = QGroupBox("Extraction Options")
        options_layout = QFormLayout()
        
        self.recursive_checkbox = QCheckBox("Include subfolders")
        self.recursive_checkbox.setChecked(True)
        
        options_layout.addRow(self.recursive_checkbox)
        options_group.setLayout(options_layout)
        
        top_controls.addWidget(folder_btn)
        top_controls.addWidget(self.folder_label, 1)
        top_controls.addWidget(options_group)
        
        # Extract button 
        extract_btn = QPushButton("Extract Metadata")
        extract_btn.clicked.connect(self.extract_metadata)
        extract_btn.setMinimumHeight(50)
        
        # File list
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(2)
        self.file_table.setHorizontalHeaderLabels(["Filename", "Status"])
        self.file_table.horizontalHeader().setStretchLastSection(True)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        
        # Add widgets to layout
        layout.addLayout(top_controls)
        layout.addWidget(extract_btn)
        layout.addWidget(self.file_table)
        layout.addWidget(self.progress_bar)
    
    def setup_edit_tab(self, tab):
        layout = QVBoxLayout(tab)
        
        # Top controls
        top_controls = QHBoxLayout()
        
        save_btn = QPushButton("Save to CSV")
        save_btn.clicked.connect(self.save_to_csv)
        
        load_btn = QPushButton("Load from CSV")
        load_btn.clicked.connect(self.load_from_csv)
        
        self.csv_label = QLabel("No CSV file loaded")
        
        top_controls.addWidget(save_btn)
        top_controls.addWidget(load_btn)
        top_controls.addWidget(self.csv_label, 1)
        
        # Metadata table
        self.metadata_table = QTableWidget()
        self.metadata_table.setColumnCount(9)  # Updated to include year
        self.metadata_table.setHorizontalHeaderLabels([
            "Filename", "Title", "Artist", "Album", 
            "Album Artist", "Genre", "Year", "Track #", "Disc #"])
        
        # Set column widths (approximate proportions)
        header = self.metadata_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Filename - stretch
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Title - stretch
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # Artist - stretch
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # Album - stretch
        header.setSectionResizeMode(4, QHeaderView.Stretch)  # Album Artist - stretch
        header.setSectionResizeMode(5, QHeaderView.Interactive)  # Genre - fixed
        header.setSectionResizeMode(6, QHeaderView.Interactive)  # Year - fixed (new)
        header.setSectionResizeMode(7, QHeaderView.Interactive)  # Track # - fixed
        header.setSectionResizeMode(8, QHeaderView.Interactive)  # Disc # - fixed
        
        # Set fixed width for some columns
        self.metadata_table.setColumnWidth(5, 100)  # Genre
        self.metadata_table.setColumnWidth(6, 60)   # Year
        self.metadata_table.setColumnWidth(7, 60)   # Track #
        self.metadata_table.setColumnWidth(8, 60)   # Disc #
        
        # Bulk edit controls
        bulk_edit_group = QGroupBox("Bulk Edit")
        bulk_edit_layout = QHBoxLayout()
        
        self.bulk_field = QComboBox()
        self.bulk_field.addItems(["Title", "Artist", "Album", "Album Artist", "Genre", "Year"])  # Added Year
        
        self.bulk_value = QComboBox()
        self.bulk_value.setEditable(True)
        
        apply_btn = QPushButton("Apply to Selected")
        apply_btn.clicked.connect(self.apply_bulk_edit)
        
        bulk_edit_layout.addWidget(QLabel("Field:"))
        bulk_edit_layout.addWidget(self.bulk_field)
        bulk_edit_layout.addWidget(QLabel("Value:"))
        bulk_edit_layout.addWidget(self.bulk_value, 1)
        bulk_edit_layout.addWidget(apply_btn)
        
        bulk_edit_group.setLayout(bulk_edit_layout)
        
        # Add widgets to layout
        layout.addLayout(top_controls)
        layout.addWidget(self.metadata_table)
        layout.addWidget(bulk_edit_group)    

    def setup_update_tab(self, tab):
        layout = QVBoxLayout(tab)
        
        # Top controls
        top_controls = QHBoxLayout()
        
        # Options
        options_group = QGroupBox("Update Options")
        options_layout = QFormLayout()
        
        self.rename_checkbox = QCheckBox("Rename files with track numbers")
        self.rename_checkbox.setChecked(True)
        
        self.dry_run_checkbox = QCheckBox("Dry run (no actual changes)")
        self.dry_run_checkbox.setChecked(True)
        
        options_layout.addRow(self.rename_checkbox)
        options_layout.addRow(self.dry_run_checkbox)
        options_group.setLayout(options_layout)
        
        top_controls.addWidget(options_group)
        
        # Update button
        update_btn = QPushButton("Update Music Files")
        update_btn.clicked.connect(self.update_files)
        update_btn.setMinimumHeight(50)
        
        # Results text display
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels(["Filename", "Status", "Details"])
        self.results_table.horizontalHeader().setStretchLastSection(True)
        
        # Add widgets to layout
        layout.addLayout(top_controls)
        layout.addWidget(update_btn)
        layout.addWidget(self.results_table)
        layout.addWidget(QLabel("Note: Please save your metadata in the Edit tab before updating files."))
    
    # Functionality methods
    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Music Folder", self.current_folder)
        if folder:
            self.current_folder = folder
            self.folder_label.setText(folder)
            self.scan_folder()
    
    def scan_folder(self):
        # Scan the selected folder for music files
        self.music_files = []
        if self.recursive_checkbox.isChecked():
            for root, _, files in os.walk(self.current_folder):
                for file in files:
                    if is_audio_file(file):
                        self.music_files.append(os.path.join(root, file))
        else:
            for file in os.listdir(self.current_folder):
                filepath = os.path.join(self.current_folder, file)
                if os.path.isfile(filepath) and is_audio_file(file):
                    self.music_files.append(filepath)
        
        # Update the file table
        self.file_table.setRowCount(len(self.music_files))
        for i, filepath in enumerate(self.music_files):
            filename = os.path.basename(filepath)
            self.file_table.setItem(i, 0, QTableWidgetItem(filename))
            self.file_table.setItem(i, 1, QTableWidgetItem("Pending"))
    
    def extract_metadata(self):
        # Use a background thread for processing
        self.extraction_thread = MetadataExtractionThread(self.music_files)
        self.extraction_thread.progress_update.connect(self.update_extraction_progress)
        self.extraction_thread.finished.connect(self.extraction_finished)
        self.extraction_thread.start()
    
    def update_extraction_progress(self, index, status, metadata=None):
        # Update progress bar
        progress = (index + 1) / len(self.music_files) * 100
        self.progress_bar.setValue(int(progress))
        
        # Update file status
        self.file_table.setItem(index, 1, QTableWidgetItem(status))
        
        # If metadata was extracted, store it
        if metadata:
            self.metadata.append(metadata)
    
    def extraction_finished(self):
        # Display metadata in the edit tab
        self.populate_metadata_table()
        
        # Switch to edit tab
        tab_widget = self.centralWidget().findChild(QTabWidget)
        tab_widget.setCurrentIndex(1)
        
        QMessageBox.information(self, "Extraction Complete", 
                               f"Successfully extracted metadata from {len(self.metadata)} files.")
    
    def populate_metadata_table(self):
        # Fill the metadata table with extracted data
        self.metadata_table.setRowCount(len(self.metadata))
        for i, data in enumerate(self.metadata):
            self.metadata_table.setItem(i, 0, QTableWidgetItem(data.get('filename', '')))
            self.metadata_table.setItem(i, 1, QTableWidgetItem(data.get('title', '')))
            self.metadata_table.setItem(i, 2, QTableWidgetItem(data.get('artist', '')))
            self.metadata_table.setItem(i, 3, QTableWidgetItem(data.get('album', '')))
            self.metadata_table.setItem(i, 4, QTableWidgetItem(data.get('album_artist', '')))
            self.metadata_table.setItem(i, 5, QTableWidgetItem(data.get('genre', '')))
            self.metadata_table.setItem(i, 6, QTableWidgetItem(data.get('year', '')))  # Year column
            self.metadata_table.setItem(i, 7, QTableWidgetItem(data.get('track_number', '')))
            self.metadata_table.setItem(i, 8, QTableWidgetItem(data.get('disc_number', '')))

    def save_to_csv(self):
        # Get the save file path
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Metadata to CSV", 
                                                self.current_folder, "CSV Files (*.csv)")
        if not file_path:
            return
        
        # Update metadata from table entries
        for i in range(self.metadata_table.rowCount()):
            self.metadata[i]['title'] = self.metadata_table.item(i, 1).text()
            self.metadata[i]['artist'] = self.metadata_table.item(i, 2).text()
            self.metadata[i]['album'] = self.metadata_table.item(i, 3).text()
            self.metadata[i]['album_artist'] = self.metadata_table.item(i, 4).text()
            self.metadata[i]['genre'] = self.metadata_table.item(i, 5).text()
            self.metadata[i]['year'] = self.metadata_table.item(i, 6).text()  # Year column
            self.metadata[i]['track_number'] = self.metadata_table.item(i, 7).text()
            self.metadata[i]['disc_number'] = self.metadata_table.item(i, 8).text()
        
        # Write to CSV
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['filename', 'title', 'artist', 'album', 'album_artist', 
                        'genre', 'year', 'track_number', 'disc_number']  # Added year
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.metadata)
        
        self.csv_path = file_path
        self.csv_label.setText(file_path)
        
        QMessageBox.information(self, "Save Complete", 
                                f"Metadata saved to {file_path}")

    def load_from_csv(self):
        # Get the load file path
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Metadata from CSV", 
                                               self.current_folder, "CSV Files (*.csv)")
        if not file_path:
            return
        
        # Read from CSV
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            self.metadata = list(reader)
        
        self.csv_path = file_path
        self.csv_label.setText(file_path)
        
        # Populate table
        self.populate_metadata_table()
        
        # Update bulk edit dropdown
        self.update_bulk_values()
        
        QMessageBox.information(self, "Load Complete", 
                               f"Loaded metadata for {len(self.metadata)} files")
    
    def update_bulk_values(self):
        # Add all current unique values to the bulk edit dropdown
        field_index = {
            "Title": 1, 
            "Artist": 2, 
            "Album": 3, 
            "Album Artist": 4, 
            "Genre": 5,
            "Year": 6  # Added Year
        }
        
        field = self.bulk_field.currentText()
        idx = field_index[field]
        
        values = set()
        for i in range(self.metadata_table.rowCount()):
            text = self.metadata_table.item(i, idx).text()
            if text:
                values.add(text)
        
        self.bulk_value.clear()
        self.bulk_value.addItems(sorted(values))

    
    
    def apply_bulk_edit(self):
        # Apply the selected value to all selected rows
        field_index = {
            "Title": 1, 
            "Artist": 2, 
            "Album": 3, 
            "Album Artist": 4, 
            "Genre": 5,
            "Year": 6  # Added Year
        }
        
        field = self.bulk_field.currentText()
        value = self.bulk_value.currentText()
        idx = field_index[field]
        
        # Get selected items
        selected_items = self.metadata_table.selectedItems()
        selected_rows = set()
        for item in selected_items:
            selected_rows.add(item.row())
        
        # Apply value to all selected rows
        for row in selected_rows:
            self.metadata_table.setItem(row, idx, QTableWidgetItem(value))    

    def update_files(self):
        # Make sure we have metadata and CSV
        if not self.metadata or not self.csv_path:
            QMessageBox.warning(self, "No Metadata", 
                            "Please extract or load metadata before updating files.")
            return

        # Update metadata from table entries (in case any changes weren't saved)
        for i in range(self.metadata_table.rowCount()):
            self.metadata[i]['title'] = self.metadata_table.item(i, 1).text()
            self.metadata[i]['artist'] = self.metadata_table.item(i, 2).text()
            self.metadata[i]['album'] = self.metadata_table.item(i, 3).text()
            self.metadata[i]['album_artist'] = self.metadata_table.item(i, 4).text()
            self.metadata[i]['genre'] = self.metadata_table.item(i, 5).text()
            self.metadata[i]['year'] = self.metadata_table.item(i, 6).text()  # Year is at index 6
            self.metadata[i]['track_number'] = self.metadata_table.item(i, 7).text()  # Track # is at index 7
            self.metadata[i]['disc_number'] = self.metadata_table.item(i, 8).text()  # Disc # is at index 8
        
        # Save updated metadata to CSV
        with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['filename', 'title', 'artist', 'album', 'album_artist', 
                        'genre', 'year', 'track_number', 'disc_number']  # Added year
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.metadata)
        
        # Run the update
        dry_run = self.dry_run_checkbox.isChecked()
        rename_files = self.rename_checkbox.isChecked()
        
        self.update_thread = MetadataUpdateThread(
            self.csv_path, 
            self.current_folder, 
            dry_run,
            True,  # verbose
            self.recursive_checkbox.isChecked(),
            rename_files
        )
        
        self.update_thread.progress_update.connect(self.update_progress)
        self.update_thread.finished.connect(self.update_finished)
        
        # Clear results table
        self.results_table.setRowCount(0)
        
        # Start update
        self.update_thread.start()        
    def update_progress(self, filename, status, details):
        # Add entry to results table
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        self.results_table.setItem(row, 0, QTableWidgetItem(filename))
        self.results_table.setItem(row, 1, QTableWidgetItem(status))
        self.results_table.setItem(row, 2, QTableWidgetItem(details))
    
    def update_finished(self, stats):
        # Show summary
        status_text = (
            f"Update complete!\n"
            f"Files processed: {stats['total']}\n"
            f"Files updated: {stats['updated']}\n"
            f"Files renamed: {stats.get('renamed', 0)}\n"
            f"Files failed: {stats['failed']}\n"
            f"Files skipped: {stats['skipped']}\n"
            f"Files not found: {stats['not_found']}"
        )
        
        QMessageBox.information(self, "Update Complete", status_text)

# Worker thread classes
class MetadataExtractionThread(QThread):
    progress_update = pyqtSignal(int, str, object)
    finished = pyqtSignal()  # Add finished signal
    
    def __init__(self, files):
        super().__init__()
        self.files = files
        
    def run(self):
        for i, filepath in enumerate(self.files):
            try:
                filename = os.path.basename(filepath)
                
                # Initialize tags dictionary
                tags = {
                    'filename': filename,
                    'album': '',
                    'album_artist': '',
                    'artist': '',
                    'genre': '',
                    'title': '',
                    'track_number': '',
                    'disc_number': '',
                    'year': ''  # Added year
                }
                
                # Extract tags based on file type
                if filepath.lower().endswith('.mp3'):
                    extract_mp3_tags(filepath, tags)
                elif filepath.lower().endswith('.flac'):
                    extract_flac_tags(filepath, tags)
                elif filepath.lower().endswith('.m4a'):
                    extract_m4a_tags(filepath, tags)
                elif filepath.lower().endswith('.ogg'):
                    extract_ogg_tags(filepath, tags)
                elif filepath.lower().endswith('.wma'):
                    extract_wma_tags(filepath, tags)
                
                # Extract from filename if needed
                needs_title = not tags['title']
                needs_track = not tags['track_number']
                
                if needs_title or needs_track:
                    track_from_filename, title_from_filename = extract_track_and_title_from_filename(filename)
                    
                    if needs_title:
                        tags['title'] = title_from_filename
                    
                    if needs_track and track_from_filename:
                        tags['track_number'] = track_from_filename
                
                self.progress_update.emit(i, "Processed", tags)
            except Exception as e:
                self.progress_update.emit(i, f"Error: {str(e)}", None)
        
        self.finished.emit()  # Emit finished signal when done

class MetadataUpdateThread(QThread):
    progress_update = pyqtSignal(str, str, str)
    finished = pyqtSignal(dict)
    
    def __init__(self, csv_file, input_folder, dry_run, verbose, recursive, rename_files):
        super().__init__()
        self.csv_file = csv_file
        self.input_folder = input_folder
        self.dry_run = dry_run
        self.verbose = verbose
        self.recursive = recursive
        self.rename_files = rename_files
    
    def run(self):
        # Create a local callback function that emits the signal
        def progress_callback(filename, status, details):
            self.progress_update.emit(filename, status, details)
            
        # Use the wrapper function with our local callback
        stats = update_tags_from_csv_with_callback(
            self.csv_file,
            self.input_folder,
            self.dry_run,
            self.verbose,
            self.recursive,
            self.rename_files,
            progress_callback
        )
        
        self.finished.emit(stats)

# Main application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Modern look across platforms
    window = MusicMetadataManager()
    window.show()
    sys.exit(app.exec_())