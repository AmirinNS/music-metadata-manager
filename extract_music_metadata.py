#!/usr/bin/env python3
import os
import csv
import re
import argparse
import mutagen
from mutagen.mp3 import MP3
from mutagen.id3 import ID3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from mutagen.oggvorbis import OggVorbis
from mutagen.asf import ASF  # For WMA files

def extract_tags(directory, output_file, recursive=False, verbose=False):
    """
    Extract music tag data and export as CSV with specific columns
    
    Args:
        directory: Directory containing music files
        output_file: Path to the output CSV file
        recursive: If True, search subdirectories recursively
        verbose: If True, print detailed information
    """
    # Columns we want in the CSV
    csv_columns = ['album', 'album_artist', 'artist', 'genre', 'title', 'track_number', 'filename']
    
    # Create a list to store the music file data
    music_data = []
    
    # Find music files
    if recursive:
        # Walk through the directory and its subdirectories
        for root, _, files in os.walk(directory):
            for filename in files:
                if is_audio_file(filename):
                    filepath = os.path.join(root, filename)
                    process_file(filepath, filename, music_data, verbose)
    else:
        # Only look in the specified directory
        for filename in os.listdir(directory):
            filepath = os.path.join(directory, filename)
            if os.path.isfile(filepath) and is_audio_file(filename):
                process_file(filepath, filename, music_data, verbose)
    
    # Write to CSV
    if music_data:
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
            writer.writeheader()
            writer.writerows(music_data)
        
        print(f"Successfully exported {len(music_data)} music files' tag data to {output_file}")
    else:
        print("No music files found in the specified directory.")

def is_audio_file(filename):
    """Check if a file is a supported audio file based on extension"""
    supported_extensions = ['.mp3', '.flac', '.m4a', '.ogg', '.wma']
    return any(filename.lower().endswith(ext) for ext in supported_extensions)

def extract_track_and_title_from_filename(filename):
    """
    Extract track number and title from filename patterns like:
    - '01 Title.mp3'
    - '01 - Title.mp3'
    - '01. Title.mp3'
    - '01_Title.mp3'
    - 'Track 01 - Title.mp3'
    
    Returns a tuple of (track_number, title)
    """
    # Remove file extension
    base_name = os.path.splitext(filename)[0]
    
    # Define patterns to match
    patterns = [
        # 01 Title or 01-Title or 01. Title or 01_Title
        r'^(\d+)[\s\-\._]+(.+)$',
        # Track 01 - Title
        r'^Track\s+(\d+)[\s\-\._]+(.+)$',
        # CD1-01 Title
        r'^CD\d+[\-\._](\d+)[\s\-\._]+(.+)$',
        # Disc 1-01 Title
        r'^Disc\s*\d+[\-\._](\d+)[\s\-\._]+(.+)$'
    ]
    
    # Try each pattern
    for pattern in patterns:
        match = re.match(pattern, base_name)
        if match:
            track_number = match.group(1)
            title = match.group(2)
            
            # Clean up the title
            title = title.strip()
            title = re.sub(r'[\-_\.]+', ' ', title)  # Replace separators with spaces
            title = ' '.join(word.capitalize() for word in title.split())  # Capitalize
            
            return track_number, title
    
    # If no track number found in filename, return empty track and use whole filename as title
    title = base_name.replace('_', ' ').replace('-', ' ').replace('.', ' ')
    title = ' '.join(word.capitalize() for word in title.split())
    
    return '', title.strip()

def process_file(filepath, filename, music_data, verbose):
    """Process a single audio file and extract its tags"""
    try:
        # Initialize tags dictionary with default values
        tags = {
            'album': '',
            'album_artist': '',
            'artist': '',
            'genre': '',
            'title': '',
            'track_number': '',
            'filename': filename
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
        
        # If title or track_number is empty, extract from filename
        needs_title = not tags['title']
        needs_track = not tags['track_number']
        
        if needs_title or needs_track:
            track_from_filename, title_from_filename = extract_track_and_title_from_filename(filename)
            
            if needs_title:
                tags['title'] = title_from_filename
                if verbose:
                    print(f"  Using filename as title for: {filename} -> {tags['title']}")
            
            if needs_track and track_from_filename:
                tags['track_number'] = track_from_filename
                if verbose:
                    print(f"  Using filename as track number for: {filename} -> {tags['track_number']}")
        
        if verbose:
            print(f"Processed: {filepath}")
            if verbose > 1:  # Extra verbose
                print(f"  Tags: {tags}")
        
        music_data.append(tags)
    except Exception as e:
        print(f"Error processing {filepath}: {e}")

def extract_mp3_tags(filepath, tags):
    """Extract tags from MP3 file"""
    try:
        # Try using ID3 tags first
        audio = ID3(filepath)
        
        # Map ID3 tag names to our tag names
        id3_map = {
            'TIT2': 'title',
            'TPE1': 'artist',
            'TPE2': 'album_artist',
            'TALB': 'album',
            'TCON': 'genre',
            'TRCK': 'track_number'
        }
        
        for id3_tag, tag_name in id3_map.items():
            if id3_tag in audio:
                tags[tag_name] = str(audio[id3_tag].text[0])
    except:
        # Fallback to MP3 if ID3 fails
        try:
            audio = MP3(filepath)
            # Basic extraction for MP3 files without ID3 tags
            for key in audio:
                if 'title' in key.lower():
                    tags['title'] = str(audio[key])
                elif 'artist' in key.lower() and 'album' not in key.lower():
                    tags['artist'] = str(audio[key])
                elif 'album artist' in key.lower():
                    tags['album_artist'] = str(audio[key])
                elif 'album' in key.lower():
                    tags['album'] = str(audio[key])
                elif 'genre' in key.lower():
                    tags['genre'] = str(audio[key])
                elif 'track' in key.lower() and 'number' in key.lower():
                    tags['track_number'] = str(audio[key])
        except:
            # Just continue if both methods fail
            pass

def extract_flac_tags(filepath, tags):
    """Extract tags from FLAC file"""
    audio = FLAC(filepath)
    
    # Map FLAC tag names to our tag names
    flac_map = {
        'TITLE': 'title',
        'ARTIST': 'artist',
        'ALBUMARTIST': 'album_artist',
        'ALBUM': 'album',
        'GENRE': 'genre',
        'TRACKNUMBER': 'track_number'
    }
    
    for flac_tag, tag_name in flac_map.items():
        if flac_tag in audio:
            tags[tag_name] = audio[flac_tag][0]

def extract_m4a_tags(filepath, tags):
    """Extract tags from M4A file"""
    audio = MP4(filepath)
    
    # Map M4A tag names to our tag names
    m4a_map = {
        '©nam': 'title',
        '©ART': 'artist',
        'aART': 'album_artist',
        '©alb': 'album',
        '©gen': 'genre'
    }
    
    for m4a_tag, tag_name in m4a_map.items():
        if m4a_tag in audio:
            tags[tag_name] = audio[m4a_tag][0]
    
    # Special handling for track number
    if 'trkn' in audio and audio['trkn']:
        if len(audio['trkn'][0]) > 0:
            tags['track_number'] = str(audio['trkn'][0][0])

def extract_ogg_tags(filepath, tags):
    """Extract tags from OGG file"""
    audio = OggVorbis(filepath)
    
    # Map OGG tag names to our tag names
    ogg_map = {
        'TITLE': 'title',
        'ARTIST': 'artist',
        'ALBUMARTIST': 'album_artist',
        'ALBUM': 'album',
        'GENRE': 'genre',
        'TRACKNUMBER': 'track_number'
    }
    
    for ogg_tag, tag_name in ogg_map.items():
        if ogg_tag in audio:
            tags[tag_name] = audio[ogg_tag][0]

def extract_wma_tags(filepath, tags):
    """Extract tags from WMA file"""
    audio = ASF(filepath)
    
    # Map WMA tag names to our tag names
    wma_map = {
        'Title': 'title',
        'Author': 'artist',
        'WM/AlbumArtist': 'album_artist',
        'WM/AlbumTitle': 'album',
        'WM/Genre': 'genre',
        'WM/TrackNumber': 'track_number'
    }
    
    for wma_tag, tag_name in wma_map.items():
        if wma_tag in audio:
            tags[tag_name] = str(audio[wma_tag][0])

def main():
    parser = argparse.ArgumentParser(description='Extract music tag data and export as CSV')
    parser.add_argument('directory', help='Directory containing music files')
    parser.add_argument('-o', '--output', default='music_tags.csv', help='Output CSV file name')
    parser.add_argument('-r', '--recursive', action='store_true', help='Search subdirectories recursively')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    parser.add_argument('-vv', '--very-verbose', action='store_true', help='Enable very verbose output (shows all tags)')
    
    args = parser.parse_args()
    
    # Normalize directory path
    directory = os.path.normpath(os.path.expanduser(args.directory))
    
    if not os.path.isdir(directory):
        print(f"Error: {directory} is not a valid directory")
        return 1
    
    # Set verbosity level
    verbose = 2 if args.very_verbose else 1 if args.verbose else 0
    
    try:
        extract_tags(directory, args.output, args.recursive, verbose)
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())