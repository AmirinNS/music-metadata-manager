# Music Metadata Manager with Video Converter

A comprehensive GUI application for converting videos to MP3, extracting metadata, editing tags, and updating music files. This tool provides a complete workflow for managing your music collection from video downloads to properly tagged audio files.

## Project Structure

```
music-metadata-manager/
├── gui_with_converter.py          # Main GUI application with video conversion
├── convert_video_to_mp3.py        # Video conversion script
├── extract_music_metadata.py      # Metadata extraction script
├── update_music_metadata.py       # Metadata update script
├── requirements.txt               # Python dependencies
└── README.md                      # This file
```

## Technical Details

### Video Conversion Process

The video conversion uses FFmpeg with the following parameters:
- **Codec**: libmp3lame (high-quality MP3 encoder)
- **Sample Rate**: 44.1 kHz (CD quality)
- **Channels**: Stereo (2 channels)
- **Bitrates**: 128k, 192k, 256k, 320k (user selectable)

### Threading Architecture

The application uses multi-threading for responsive UI:
- `VideoConversionThread`: Handles video-to-MP3 conversion
- `MetadataExtractionThread`: Processes metadata extraction
- `MetadataUpdateThread`: Manages file updates

### Error Handling

- **FFmpeg availability check** on startup
- **Graceful degradation** when FFmpeg is not available
- **Comprehensive error reporting** during conversion and processing
- **Progress tracking** with detailed status messages

## Configuration Options

### Video Conversion Settings

- **Quality presets**: 128k (good), 192k (very good), 256k (excellent), 320k (best)
- **Output organization**: Maintain folder structure in output directory
- **Metadata preservation**: Copy video metadata to MP3 tags
- **Overwrite control**: Skip or replace existing files

### Filename Patterns

The application recognizes these filename patterns for track extraction:
- `01 Title.mp4` → Track 1, Title "Title"
- `01 - Title.mp4` → Track 1, Title "Title"
- `01. Title.mp4` → Track 1, Title "Title"
- `Track 01 - Title.mp4` → Track 1, Title "Title"
- `CD1-01 Title.mp4` → Disc 1, Track 1, Title "Title"

## Workflow Examples

### Complete Video-to-Music Workflow

1. **Download music videos** and organize by album in folders
2. **Convert videos** using the Convert Videos tab
3. **Extract metadata** from the converted MP3 files
4. **Edit tags** to add missing information (album, artist, etc.)
5. **Update files** to apply the metadata and rename with track numbers

### Batch Processing Large Collections

1. **Organize videos** in album folders under a main directory
2. **Enable recursive scanning** to process all subfolders
3. **Use separate output folder** to keep originals intact
4. **Process in batches** if dealing with very large collections
5. **Verify results** using dry-run mode before final update

## Troubleshooting

### Common Issues

**FFmpeg not found:**
- Ensure FFmpeg is installed and in your system PATH
- Test with `ffmpeg -version` in command prompt/terminal
- Restart the application after installing FFmpeg

**Conversion failures:**
- Check if video files are corrupted
- Ensure sufficient disk space for output files
- Some DRM-protected videos cannot be converted

**Metadata not extracted:**
- Some video files may not contain metadata
- Use filename parsing as fallback
- Manually edit metadata in the GUI

**File update errors:**
- Check file permissions (read-only files cannot be updated)
- Close other applications that might be using the files
- Use dry-run mode to test changes first

### Performance Tips

**For large collections:**
- Process folders in smaller batches
- Use SSD storage for faster I/O operations
- Close other applications to free up system resources
- Consider using lower quality settings for faster conversion

**Memory optimization:**
- Process videos in separate sessions if memory is limited
- Clear completed conversions from the table regularly
- Restart the application for very large processing jobs

## Advanced Usage

### Custom FFmpeg Parameters

For advanced users, you can modify the conversion parameters in `convert_video_to_mp3.py`:

```python
# Example: Add custom audio filters
cmd.extend(['-af', 'volume=0.8'])  # Reduce volume by 20%

# Example: Variable bitrate encoding
cmd.extend(['-q:a', '2'])  # VBR quality level 2
```

### Metadata Field Mapping

The application maps video metadata to audio tags:

| Video Field | Audio Tag | Description |
|-------------|-----------|-------------|
| title | title | Song title |
| artist | artist | Performing artist |
| album | album | Album name |
| date | year | Release year |
| genre | genre | Music genre |
| track | track_number | Track number |

### CSV Format

The exported CSV contains these columns:
- `filename`: Original filename
- `title`: Song title
- `artist`: Performing artist
- `album`: Album name
- `album_artist`: Album artist (for compilations)
- `genre`: Music genre
- `year`: Release year
- `track_number`: Track number
- `disc_number`: Disc number (for multi-disc albums)

## Integration with Other Tools

### External Editors

Export CSV files for editing in:
- **Microsoft Excel**: Full spreadsheet editing
- **LibreOffice Calc**: Free alternative to Excel
- **Google Sheets**: Cloud-based collaborative editing
- **Text editors**: Simple find-and-replace operations

### Music Players

The generated MP3 files work with:
- **Media players**: VLC, Windows Media Player, QuickTime
- **Music apps**: iTunes, Spotify (for local files), foobar2000
- **Mobile apps**: Most Android and iOS music players
- **Streaming**: Plex, Jellyfin for home media servers

## Security and Privacy

- **No network access**: All processing is done locally
- **No data collection**: No usage statistics or personal data is transmitted
- **File safety**: Original video files are never modified (unless overwrite is enabled)
- **Metadata privacy**: All tag information remains on your local system

## Contributing

### Bug Reports

When reporting bugs, please include:
- Operating system and version
- Python version
- FFmpeg version (`ffmpeg -version`)
- Steps to reproduce the issue
- Error messages or screenshots

### Feature Requests

Consider including:
- Use case description
- Expected behavior
- Any alternative solutions you've tried

### Development Setup

1. Fork the repository
2. Create a feature branch
3. Install development dependencies
4. Make your changes
5. Test with various file formats
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- **[Mutagen](https://mutagen.readthedocs.io/)** for audio metadata handling
- **[PyQt5](https://www.riverbankcomputing.com/software/pyqt/)** for the GUI framework
- **[FFmpeg](https://ffmpeg.org/)** for video/audio conversion capabilities
- **Community contributors** for testing and feedback

## Changelog

### Version 2.0.0
- ✨ Added video-to-MP3 conversion functionality
- ✨ Integrated FFmpeg for high-quality audio encoding
- ✨ Added complete workflow from videos to tagged MP3s
- ✨ Enhanced GUI with video conversion tab
- 🐛 Fixed metadata extraction from filename patterns
- 📚 Updated documentation with conversion features

### Version 1.0.0
- ✨ Initial release with metadata extraction and editing
- ✨ Support for multiple audio formats
- ✨ CSV import/export functionality
- ✨ Bulk editing capabilities Features

### 🎬 Video Conversion
- **Convert video files to MP3** using FFmpeg with high-quality audio encoding
- **Batch conversion** for processing entire folders of video files
- **Multiple video formats** supported (MP4, AVI, MKV, MOV, WMV, FLV, WebM, etc.)
- **Quality control** with selectable bitrates (128k, 192k, 256k, 320k)
- **Metadata preservation** from video files to MP3 tags
- **Flexible output options** (same folder or separate output folder)

### 🎵 Metadata Management
- **Extract metadata** from multiple audio file formats (MP3, FLAC, M4A, OGG, WMA)
- **Edit metadata** in a spreadsheet-like interface
- **Bulk edit** features for quickly updating multiple files
- **Smart filename parsing** to extract track numbers and titles
- **Rename files** with track number and disc number prefixes
- **CSV import/export** for external editing and backup

### 🔄 Complete Workflow
1. **Convert** video files to MP3
2. **Extract** metadata from converted files
3. **Edit** tags in the GUI
4. **Update** files with new metadata

## Installation

### Prerequisites

- **Python 3.6+**
- **PyQt5**
- **Mutagen library**
- **FFmpeg** (for video conversion)

### FFmpeg Installation

**Windows:**
1. Download FFmpeg from https://ffmpeg.org/download.html
2. Extract to a folder (e.g., `C:\ffmpeg`)
3. Add the `bin` folder to your system PATH

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**CentOS/RHEL:**
```bash
# Enable EPEL repository first
sudo yum install epel-release
sudo yum install ffmpeg
```

### Python Dependencies

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/music-metadata-manager.git
   cd music-metadata-manager
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python gui_with_converter.py
   ```

## User Guide

### Converting Videos to MP3

1. Click on the **Convert Videos** tab
2. Click **Select Video Folder** and choose the folder containing your video files
3. Configure conversion options:
   - **Include subfolders**: Search nested directories
   - **Audio quality**: Choose bitrate (192k recommended)
   - **Output folder**: Optionally use a separate output folder
   - **Overwrite existing**: Replace existing MP3 files
   - **Preserve metadata**: Keep video metadata in MP3 tags
4. Click **Convert Videos to MP3** to start the conversion
5. Monitor progress in the table and progress bar
6. When complete, you'll be prompted to extract metadata from the converted files

### Extracting Metadata

1. In the **Extract Metadata** tab, select your music folder
2. Check **Include subfolders** if needed
3. Click **Extract Metadata** to scan and read tag information
4. Once complete, you'll automatically be taken to the Edit tab

### Editing Metadata

1. Review and edit metadata in the table
2. Use **Bulk Edit** to update multiple files:
   - Select rows to modify
   - Choose the field to edit
   - Enter or select the new value
   - Click **Apply to Selected**
3. Save your changes to CSV format

### Updating Files

1. In the **Update Files** tab, configure options:
   - **Rename files**: Add track numbers to filenames
   - **Dry run**: Test changes without modifying files
2. Click **Update Music Files** to apply metadata changes
3. Review the results in the table

## Supported File Formats

### Video Input Formats
- MP4, AVI, MKV, MOV, WMV, FLV, WebM
- M4V, 3GP, OGV, TS, MTS, M2TS

### Audio Output/Processing Formats
- MP3 (primary output format)
- FLAC, M4A, OGG, WMA (for existing audio files)

## Command Line Interface

### Video Conversion Script

```bash
python convert_video_to_mp3.py /path/to/videos -o /output/folder -q 192k -r --overwrite
```

Options:
- `-o, --output`: Output file or folder
- `-q, --quality`: Audio quality/bitrate (default: 192k)
- `-r, --recursive`: Search subdirectories
- `--no-metadata`: Don't preserve video metadata
- `--overwrite`: Overwrite existing files
- `-v, --verbose`: Verbose output

### Metadata Extraction Script

```bash
python extract_music_metadata.py /path/to/music -o metadata.csv -r -v
```

### Metadata Update Script

```bash
python update_music_metadata.py metadata.csv /path/to/music -r -n
```

##