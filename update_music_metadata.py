#!/usr/bin/env python3
import os
import csv
import sys
import re
import argparse
import mutagen
from mutagen.mp3 import MP3, EasyMP3
from mutagen.id3 import ID3, TIT2, TPE1, TPE2, TALB, TRCK, TCON, TPOS
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from mutagen.oggvorbis import OggVorbis
from mutagen.asf import ASF  # For WMA files

def update_tags_from_csv(csv_file, input_folder, dry_run=False, verbose=False, recursive=False, rename_files=False):
    """
    Update audio file tags from a CSV file using filename and input folder
    
    Args:
        csv_file: Path to the CSV file
        input_folder: Folder containing the audio files
        dry_run: If True, don't actually change any files
        verbose: If True, print detailed information
        recursive: If True, search for files recursively in subfolders
        rename_files: If True, rename files to include track numbers
    """
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
        for row in reader:
            stats['total'] += 1
            
            # Get the filename
            filename = row.get('filename', '').strip()
            if not filename:
                print("Skipping row with empty filename")
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
                print(f"File not found: {filename}")
                stats['not_found'] += 1
                continue
            
            # Skip rows with empty data for all tag columns
            if all(not row.get(col, '') for col in available_tags):
                print(f"Skipping {filename} - no tag data provided")
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
                    print(f"Unsupported file type: {filepath}")
                    stats['skipped'] += 1
                    continue
                
                stats['updated'] += 1
                
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
                        filepath = new_filepath
                
                if verbose or dry_run:
                    print(f"Updated tags for {filename}")
                
            except Exception as e:
                stats['failed'] += 1
                print(f"Error updating {filename}: {e}")
    
    # Print statistics
    print("\nUpdate complete:")
    print(f"Total files processed: {stats['total']}")
    print(f"Files updated: {stats['updated']}")
    if rename_files:
        print(f"Files renamed: {stats['renamed']}")
    print(f"Files failed: {stats['failed']}")
    print(f"Files skipped: {stats['skipped']}")
    print(f"Files not found: {stats['not_found']}")
    
    if dry_run:
        print("\nThis was a dry run - no files were actually modified.")

def rename_file_with_track_number(filepath, track_number, dry_run, verbose, disc_number=None):
    """
    Rename a file to include track number and optional disc number if they're missing.
    If disc_number is provided, the format will be "disc-track filename.ext" (e.g., "1-01 Title.mp3")
    Returns the new filepath if renamed, or the original filepath if not.
    """
    dirname = os.path.dirname(filepath)
    filename = os.path.basename(filepath)
    extension = os.path.splitext(filename)[1]
    file_base = os.path.splitext(filename)[0]
    
    # Check if the filename already starts with a proper track number or disc-track pattern
    has_track_pattern = re.match(r'^\d+[\s\-\._]', file_base) or re.match(r'^Track\s+\d+', file_base)
    has_disc_track_pattern = re.match(r'^\d+\-\d+[\s\-\._]', file_base)
    
    # If disc number is provided, check for disc-track pattern, otherwise just check for track pattern
    if (disc_number and has_disc_track_pattern) or (not disc_number and has_track_pattern):
        # File already has the proper numbering pattern, no need to rename
        return filepath
    
    # Format the track number with leading zeros if needed
    if track_number.isdigit():
        # Pad track number to 2 digits
        formatted_track = track_number.zfill(2)
    else:
        formatted_track = track_number
    
    # If disc number is provided, create a disc-track prefix
    if disc_number:
        # Use disc number as is (no leading zeros)
        prefix = f"{disc_number}-{formatted_track}"
    else:
        prefix = formatted_track
    
    # Create new filename
    new_filename = f"{prefix} {file_base}{extension}"
    new_filepath = os.path.join(dirname, new_filename)
    
    if verbose:
        print(f"  Renaming: {filename} -> {new_filename}")
    
    if not dry_run:
        try:
            os.rename(filepath, new_filepath)
            return new_filepath
        except Exception as e:
            print(f"  Error renaming file: {e}")
            return filepath
    
    return filepath

def is_audio_file(filename):
    """Check if a file is a supported audio file based on extension"""
    supported_extensions = ['.mp3', '.flac', '.m4a', '.ogg', '.wma']
    return any(filename.lower().endswith(ext) for ext in supported_extensions)

def update_mp3_tags(filepath, data, available_tags, dry_run, verbose):
    """Update tags for MP3 files"""
    if verbose:
        print(f"Updating MP3 tags for {filepath}")
    
    if not dry_run:
        try:
            # Use EasyMP3 for simpler tag handling
            audio = EasyMP3(filepath)
            
            # Map CSV columns to MP3 tag names (for EasyMP3)
            mp3_map = {
                'title': 'title',
                'artist': 'artist',
                'album': 'album',
                'genre': 'genre',
                'track_number': 'tracknumber',
                'disc_number': 'discnumber',
                'composer': 'composer',
                'year': 'date',
                'comment': 'comment'
            }
            
            # Update tags if present in the data
            for csv_col in available_tags:
                if csv_col in mp3_map and data.get(csv_col):
                    try:
                        audio[mp3_map[csv_col]] = data[csv_col]
                    except:
                        if verbose:
                            print(f"  Warning: Could not set {csv_col} tag")
            
            # Save the changes
            audio.save()
            
            # For tags requiring ID3 directly (album_artist)
            if 'album_artist' in available_tags and data.get('album_artist'):
                try:
                    id3 = ID3(filepath)
                    id3.add(TPE2(encoding=3, text=data['album_artist']))
                    
                    # Also add disc number if specified (more reliable with ID3)
                    if 'disc_number' in available_tags and data.get('disc_number'):
                        id3.add(TPOS(encoding=3, text=data['disc_number']))
                        
                    id3.save()
                except:
                    if verbose:
                        print(f"  Warning: Could not set album_artist/disc_number with ID3")
        except Exception as e:
            raise Exception(f"Error updating MP3 tags: {str(e)}")

def update_flac_tags(filepath, data, available_tags, dry_run, verbose):
    """Update tags for FLAC files"""
    if verbose:
        print(f"Updating FLAC tags for {filepath}")
    
    if not dry_run:
        try:
            audio = FLAC(filepath)
            
            # Map CSV columns to FLAC tag names
            flac_map = {
                'title': 'TITLE',
                'artist': 'ARTIST',
                'album_artist': 'ALBUMARTIST',
                'album': 'ALBUM',
                'genre': 'GENRE',
                'track_number': 'TRACKNUMBER',
                'disc_number': 'DISCNUMBER',
                'composer': 'COMPOSER',
                'year': 'DATE',
                'comment': 'COMMENT'
            }
            
            # Update tags if present in the data
            for csv_col in available_tags:
                if csv_col in flac_map and data.get(csv_col):
                    audio[flac_map[csv_col]] = [data[csv_col]]
            
            # Save the changes
            audio.save()
        except Exception as e:
            raise Exception(f"Error updating FLAC tags: {str(e)}")

def update_m4a_tags(filepath, data, available_tags, dry_run, verbose):
    """Update tags for M4A files"""
    if verbose:
        print(f"Updating M4A tags for {filepath}")
    
    if not dry_run:
        try:
            audio = MP4(filepath)
            
            # Map CSV columns to M4A tag names
            m4a_map = {
                'title': '©nam',
                'artist': '©ART',
                'album_artist': 'aART',
                'album': '©alb',
                'genre': '©gen',
                'composer': '©wrt',
                'year': '©day',
                'comment': '©cmt'
            }
            
            # Update tags if present in the data
            for csv_col in available_tags:
                if csv_col in m4a_map and data.get(csv_col):
                    audio[m4a_map[csv_col]] = [data[csv_col]]
            
            # Special handling for track number
            if 'track_number' in available_tags and data.get('track_number'):
                try:
                    # Try to preserve total tracks if present
                    track_num = int(data['track_number'])
                    
                    # Check if there's an existing trkn tag to preserve total tracks
                    if 'trkn' in audio and audio['trkn']:
                        try:
                            total_tracks = audio['trkn'][0][1]
                            audio['trkn'] = [(track_num, total_tracks)]
                        except (IndexError, TypeError):
                            audio['trkn'] = [(track_num, 0)]
                    else:
                        audio['trkn'] = [(track_num, 0)]
                except ValueError:
                    # If track number isn't a valid integer, skip it
                    if verbose:
                        print(f"  Warning: Invalid track number: {data['track_number']}")
            
            # Special handling for disc number
            if 'disc_number' in available_tags and data.get('disc_number'):
                try:
                    # Try to preserve total discs if present
                    disc_num = int(data['disc_number'])
                    
                    # Check if there's an existing disk tag to preserve total discs
                    if 'disk' in audio and audio['disk']:
                        try:
                            total_discs = audio['disk'][0][1]
                            audio['disk'] = [(disc_num, total_discs)]
                        except (IndexError, TypeError):
                            audio['disk'] = [(disc_num, 0)]
                    else:
                        audio['disk'] = [(disc_num, 0)]
                except ValueError:
                    # If disc number isn't a valid integer, skip it
                    if verbose:
                        print(f"  Warning: Invalid disc number: {data['disc_number']}")
            
            # Save the changes
            audio.save()
        except Exception as e:
            raise Exception(f"Error updating M4A tags: {str(e)}")

def update_ogg_tags(filepath, data, available_tags, dry_run, verbose):
    """Update tags for OGG files"""
    if verbose:
        print(f"Updating OGG tags for {filepath}")
    
    if not dry_run:
        try:
            audio = OggVorbis(filepath)
            
            # Map CSV columns to OGG tag names
            ogg_map = {
                'title': 'TITLE',
                'artist': 'ARTIST',
                'album_artist': 'ALBUMARTIST',
                'album': 'ALBUM',
                'genre': 'GENRE',
                'track_number': 'TRACKNUMBER',
                'disc_number': 'DISCNUMBER',
                'composer': 'COMPOSER',
                'year': 'DATE',
                'comment': 'COMMENT'
            }
            
            # Update tags if present in the data
            for csv_col in available_tags:
                if csv_col in ogg_map and data.get(csv_col):
                    audio[ogg_map[csv_col]] = [data[csv_col]]
            
            # Save the changes
            audio.save()
        except Exception as e:
            raise Exception(f"Error updating OGG tags: {str(e)}")

def update_wma_tags(filepath, data, available_tags, dry_run, verbose):
    """Update tags for WMA files"""
    if verbose:
        print(f"Updating WMA tags for {filepath}")
    
    if not dry_run:
        try:
            audio = ASF(filepath)
            
            # Map CSV columns to WMA tag names
            wma_map = {
                'title': 'Title',
                'artist': 'Author',
                'album_artist': 'WM/AlbumArtist',
                'album': 'WM/AlbumTitle',
                'genre': 'WM/Genre',
                'track_number': 'WM/TrackNumber',
                'disc_number': 'WM/PartOfSet',
                'composer': 'WM/Composer',
                'year': 'WM/Year',
                'comment': 'Description'
            }
            
            # Update tags if present in the data
            for csv_col in available_tags:
                if csv_col in wma_map and data.get(csv_col):
                    audio[wma_map[csv_col]] = [data[csv_col]]
            
            # Save the changes
            audio.save()
        except Exception as e:
            raise Exception(f"Error updating WMA tags: {str(e)}")

def main():
    # Create a custom argument parser that handles spaces better
    parser = argparse.ArgumentParser(description='Update audio file tags from a CSV file')
    
    try:
        parser.add_argument('csv_file', help='Path to the CSV file with tag data')
        parser.add_argument('input_folder', help='Folder containing the audio files')
        parser.add_argument('-d', '--dry-run', action='store_true', 
                            help='Dry run mode - do not actually modify any files')
        parser.add_argument('-v', '--verbose', action='store_true', 
                            help='Verbose output')
        parser.add_argument('-r', '--recursive', action='store_true',
                            help='Search for files recursively in subfolders')
        parser.add_argument('-n', '--rename-files', action='store_true',
                            help='Rename files to include track numbers if missing')
        
        # Parse arguments
        args = parser.parse_args()
        
        # Normalize paths to handle spaces and special characters
        csv_file = os.path.normpath(os.path.expanduser(args.csv_file))
        input_folder = os.path.normpath(os.path.expanduser(args.input_folder))
        
        if not os.path.isfile(csv_file):
            print(f"Error: CSV file not found: {csv_file}")
            return 1
        
        if not os.path.isdir(input_folder):
            print(f"Error: Input folder does not exist: {input_folder}")
            return 1
        
        update_tags_from_csv(csv_file, input_folder, args.dry_run, args.verbose, args.recursive, args.rename_files)
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nUsage examples:")
        print("  ./update_music_tags.py metadata.csv /path/to/music")
        print("  ./update_music_tags.py \"metadata with spaces.csv\" \"/path/with spaces/music\"")
        print("  ./update_music_tags.py metadata.csv /path/to/music --recursive --verbose --rename-files")
        return 1

if __name__ == "__main__":
    sys.exit(main())