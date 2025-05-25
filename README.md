# Music Metadata Manager

A GUI application for extracting, editing, and updating metadata in music files. This tool helps you manage your music collection by providing easy access to tag information and allowing batch updates across multiple files.

## Features

- **Extract metadata** from multiple audio file formats (MP3, FLAC, M4A, OGG, WMA)
- **Edit metadata** in a spreadsheet-like interface
- **Bulk edit** features for quickly updating multiple files
- **Smart filename parsing** to extract track numbers and titles
- **Rename files** with track number and disc number prefixes
- **CSV import/export** for external editing and backup
- **Multi-format support** for all common audio file types

## Installation

### Prerequisites

- Python 3.6+
- PyQt5
- Mutagen library

### Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/music-metadata-manager.git
   cd music-metadata-manager
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python gui.py
   ```

## User Guide

### Extracting Metadata

1. Click on the **Extract Metadata** tab
2. Click **Select Music Folder** and choose the folder containing your music files
3. Check **Include subfolders** if you want to scan nested directories
4. Click **Extract Metadata** to begin the extraction process
5. Once complete, you'll automatically be taken to the Edit Metadata tab

### Editing Metadata

1. In the **Edit Metadata** tab, you'll see all extracted metadata in a table
2. Edit any cell directly by clicking on it
3. To edit multiple files at once:
   - Select the rows you want to modify (use Ctrl+click or Shift+click)
   - Choose the field to edit in the **Bulk Edit** dropdown
   - Enter or select the value you want to apply
   - Click **Apply to Selected** to update all selected rows

4. To save your changes:
   - Click **Save to CSV** to save the metadata to a CSV file
   - This CSV can be edited externally (e.g., in Excel or LibreOffice Calc)

5. To load previously saved metadata:
   - Click **Load from CSV** and select a previously saved CSV file

### Updating Files

1. In the **Update Files** tab, you can apply your edited metadata to the music files
2. Options:
   - **Rename files with track numbers**: Adds track numbers (and disc numbers if available) to the beginning of filenames
   - **Dry run**: Simulates the update without actually modifying any files

3. Click **Update Music Files** to apply the changes
4. A summary will be displayed when the update is complete

## Command Line Interface

The application also provides command-line scripts for automation purposes:

### Extract Metadata Script

```bash
python extract_music_metadata.py /path/to/music/directory -o output.csv -r
```

Options:
- `-o, --output`: Specify output CSV file (default: music_tags.csv)
- `-r, --recursive`: Search subdirectories recursively
- `-v, --verbose`: Enable verbose output
- `-vv, --very-verbose`: Enable very verbose output (shows all tags)

### Update Metadata Script

```bash
python update_music_metadata.py metadata.csv /path/to/music/directory -r -n
```

Options:
- `-d, --dry-run`: Test changes without modifying files
- `-v, --verbose`: Enable verbose output
- `-r, --recursive`: Search subdirectories recursively
- `-n, --rename-files`: Rename files with track numbers if missing

## For Developers

### Project Structure

- `gui.py`: Main GUI application file
- `extract_music_metadata.py`: Script for extracting metadata from music files
- `update_music_metadata.py`: Script for updating music files with metadata from CSV

### Core Components

1. **Extraction Module**
   - Contains functions for reading metadata from various audio formats
   - Uses the `mutagen` library to handle different tag formats
   - Includes filename parsing logic to extract information from filenames

2. **Update Module**
   - Provides functions for writing metadata back to audio files
   - Includes file rename functionality
   - Handles mappings between CSV fields and specific audio format tags

3. **GUI Application**
   - Uses PyQt5 for the user interface
   - Implements a multi-tab interface for the different stages of metadata management
   - Uses multi-threading to keep the UI responsive during long operations

### Adding Support for New Audio Formats

To add support for a new audio format:

1. Add format detection in the `is_audio_file()` function
2. Create extraction function (e.g., `extract_xyz_tags()`)
3. Create update function (e.g., `update_xyz_tags()`)
4. Add the new format to the processing logic in both extraction and update code paths

### Threading Model

The application uses `QThread` subclasses to perform long-running operations:

- `MetadataExtractionThread`: Handles reading metadata from files
- `MetadataUpdateThread`: Manages writing metadata back to files

Each thread communicates with the main UI through Qt signals for progress updates and completion.

### Known Limitations

- Very large collections (10,000+ files) may cause high memory usage
- Unicode filename support may vary by platform
- Some advanced tags are not yet supported (e.g., album art, lyrics)

## Troubleshooting

### Common Issues

**File not found errors**
- Make sure the paths don't contain special characters
- Check that you have read/write permissions to the files

**Metadata not updating**
- Some files may be read-only or locked by another application
- Verify the CSV format matches the expected structure

**GUI performance issues**
- For very large collections, try working with smaller batches of files

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Mutagen](https://mutagen.readthedocs.io/) library for audio metadata handling
- [PyQt5](https://www.riverbankcomputing.com/software/pyqt/) for the GUI framework

## Requirements

```
mutagen==1.46.0
PyQt5==5.15.7
```