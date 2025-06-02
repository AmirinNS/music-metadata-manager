#!/usr/bin/env python3
import os
import sys
import argparse
import subprocess
import json
import platform
from pathlib import Path

def is_video_file(filename):
    """Check if a file is a supported video file based on extension"""
    video_extensions = [
        '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', 
        '.m4v', '.3gp', '.ogv', '.ts', '.mts', '.m2ts'
    ]
    return any(filename.lower().endswith(ext) for ext in video_extensions)

def check_ffmpeg():
    """Check if FFmpeg is available in system PATH"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def move_to_trash(file_path):
    """
    Move file to trash/recycle bin in a cross-platform way
    Returns True if successful, False otherwise
    """
    try:
        system = platform.system().lower()
        
        if system == 'windows':
            # Windows - use send2trash if available, otherwise try shell command
            try:
                import send2trash
                send2trash.send2trash(file_path)
                return True
            except ImportError:
                # Fallback to PowerShell command
                try:
                    ps_command = f'Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile("{file_path}", "OnlyErrorDialogs", "SendToRecycleBin")'
                    subprocess.run(['powershell', '-Command', ps_command], check=True, capture_output=True)
                    return True
                except subprocess.CalledProcessError:
                    return False
                    
        elif system == 'darwin':  # macOS
            # Use osascript to move to Trash
            try:
                script = f'tell application "Finder" to delete POSIX file "{file_path}"'
                subprocess.run(['osascript', '-e', script], check=True, capture_output=True)
                return True
            except subprocess.CalledProcessError:
                # Fallback to mv to ~/.Trash
                try:
                    trash_path = os.path.expanduser('~/.Trash')
                    filename = os.path.basename(file_path)
                    dest_path = os.path.join(trash_path, filename)
                    
                    # Handle duplicate names
                    counter = 1
                    while os.path.exists(dest_path):
                        name, ext = os.path.splitext(filename)
                        dest_path = os.path.join(trash_path, f"{name}_{counter}{ext}")
                        counter += 1
                    
                    os.rename(file_path, dest_path)
                    return True
                except (OSError, IOError):
                    return False
                    
        elif system == 'linux':
            # Linux - try multiple methods
            try:
                # Method 1: Try gio (GNOME)
                subprocess.run(['gio', 'trash', file_path], check=True, capture_output=True)
                return True
            except (subprocess.CalledProcessError, FileNotFoundError):
                try:
                    # Method 2: Try kioclient5 (KDE)
                    subprocess.run(['kioclient5', 'move', file_path, 'trash:/'], check=True, capture_output=True)
                    return True
                except (subprocess.CalledProcessError, FileNotFoundError):
                    try:
                        # Method 3: Use send2trash if available
                        import send2trash
                        send2trash.send2trash(file_path)
                        return True
                    except ImportError:
                        # Method 4: Manual trash directory (XDG standard)
                        try:
                            trash_dir = os.path.expanduser('~/.local/share/Trash/files')
                            os.makedirs(trash_dir, exist_ok=True)
                            
                            filename = os.path.basename(file_path)
                            dest_path = os.path.join(trash_dir, filename)
                            
                            # Handle duplicate names
                            counter = 1
                            while os.path.exists(dest_path):
                                name, ext = os.path.splitext(filename)
                                dest_path = os.path.join(trash_dir, f"{name}_{counter}{ext}")
                                counter += 1
                            
                            os.rename(file_path, dest_path)
                            return True
                        except (OSError, IOError):
                            return False
        
        return False
        
    except Exception as e:
        print(f"Error moving file to trash: {e}")
        return False

def get_video_info(video_path):
    """Get video information using ffprobe"""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
        return None

def extract_audio_relevant_metadata(video_path):
    """Extract only audio-relevant metadata from video file"""
    info = get_video_info(video_path)
    if not info:
        return {}
    
    metadata = {}
    
    # Try to get metadata from format section
    if 'format' in info and 'tags' in info['format']:
        tags = info['format']['tags']
        
        # Only map audio-relevant metadata tags
        audio_relevant_mapping = {
            'title': 'title',
            'artist': 'artist', 
            'album': 'album',
            'album_artist': 'album_artist',
            'albumartist': 'album_artist',  # Alternative spelling
            'genre': 'genre',
            'track': 'track',
            'date': 'date',
            'year': 'date',
            'comment': 'comment',
            'composer': 'composer',
            'performer': 'artist'  # Map performer to artist
        }
        
        # Explicitly exclude these container/video-specific tags
        exclude_tags = {
            'major_brand', 'minor_version', 'compatible_brands',
            'encoder', 'encoder_settings', 'creation_time',
            'location', 'location-eng', 'com.android.version',
            'handler_name', 'vendor_id', 'timecode', 'rotate',
            'duration', 'bitrate', 'fps'
        }
        
        for tag_key, tag_value in tags.items():
            tag_key_lower = tag_key.lower()
            
            # Skip excluded tags
            if tag_key_lower in exclude_tags:
                continue
                
            # Check if this tag maps to an audio-relevant field
            if tag_key_lower in audio_relevant_mapping:
                audio_field = audio_relevant_mapping[tag_key_lower]
                if tag_value and str(tag_value).strip():
                    metadata[audio_field] = str(tag_value).strip()
    
    return metadata

def convert_video_to_mp3(video_path, output_path=None, quality='192k', 
                        preserve_metadata=True, overwrite=False, progress_callback=None,
                        clean_metadata=True, delete_video_after=False):
    """
    Convert a video file to MP3 using FFmpeg
    
    Args:
        video_path: Path to the input video file
        output_path: Path for the output MP3 file (optional)
        quality: Audio quality/bitrate (default: 192k)
        preserve_metadata: Whether to preserve metadata from video
        overwrite: Whether to overwrite existing output files
        progress_callback: Callback function for progress updates
        clean_metadata: Whether to filter out video-specific metadata
        delete_video_after: Whether to move video to trash after successful conversion
        
    Returns:
        Path to the output MP3 file if successful, None if failed
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    if not check_ffmpeg():
        raise RuntimeError("FFmpeg not found. Please install FFmpeg and ensure it's in your PATH.")
    
    # Generate output path if not provided
    if output_path is None:
        video_dir = os.path.dirname(video_path)
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        output_path = os.path.join(video_dir, f"{video_name}.mp3")
    
    # Check if output file already exists
    if os.path.exists(output_path) and not overwrite:
        if progress_callback:
            progress_callback(video_path, "Skipped", "Output file already exists")
        return None
    
    try:
        # Build FFmpeg command
        cmd = ['ffmpeg', '-i', video_path]
        
        if overwrite:
            cmd.append('-y')  # Overwrite output files
        
        # Audio encoding options
        cmd.extend([
            '-vn',  # No video
            '-acodec', 'libmp3lame',  # MP3 codec
            '-ab', quality,  # Audio bitrate
            '-ar', '44100',  # Sample rate
            '-ac', '2'  # Stereo
        ])
        
        # Handle metadata preservation
        if preserve_metadata and clean_metadata:
            # Remove all metadata first, then add only audio-relevant metadata
            cmd.extend(['-map_metadata', '-1'])  # Remove all metadata
            
            # Extract only audio-relevant metadata from the source
            audio_metadata = extract_audio_relevant_metadata(video_path)
            for key, value in audio_metadata.items():
                if value and value.strip():  # Only add non-empty values
                    # Escape special characters in metadata values
                    escaped_value = value.replace('"', '\\"')
                    cmd.extend(['-metadata', f'{key}={escaped_value}'])
            
            # Prevent FFmpeg from adding its own encoder metadata
            cmd.extend([
                '-fflags', '+bitexact',
                '-flags:a', '+bitexact'
            ])
                    
        elif preserve_metadata and not clean_metadata:
            # Copy all metadata (original behavior) - will include unwanted video metadata
            cmd.extend(['-map_metadata', '0'])
        else:
            # No metadata preservation at all
            cmd.extend([
                '-map_metadata', '-1',  # Remove all metadata
                '-fflags', '+bitexact',  # Prevent encoder metadata
                '-flags:a', '+bitexact'
            ])
        
        cmd.append(output_path)
        
        if progress_callback:
            progress_callback(video_path, "Converting", "Starting conversion...")
        
        # Run conversion
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Conversion successful - handle video deletion if requested
        conversion_message = f"Converted to {os.path.basename(output_path)}"
        
        if delete_video_after:
            if move_to_trash(video_path):
                conversion_message += " (video moved to trash)"
                if progress_callback:
                    progress_callback(video_path, "Completed", conversion_message)
            else:
                conversion_message += " (failed to move video to trash)"
                if progress_callback:
                    progress_callback(video_path, "Completed", conversion_message)
        else:
            if progress_callback:
                progress_callback(video_path, "Completed", conversion_message)
        
        return output_path
        
    except subprocess.CalledProcessError as e:
        error_msg = f"FFmpeg error: {e.stderr}"
        if progress_callback:
            progress_callback(video_path, "Failed", error_msg)
        raise RuntimeError(error_msg)
    except Exception as e:
        error_msg = f"Conversion error: {str(e)}"
        if progress_callback:
            progress_callback(video_path, "Failed", error_msg)
        raise RuntimeError(error_msg)

def batch_convert_videos(input_folder, output_folder=None, quality='192k', 
                        recursive=True, preserve_metadata=True, overwrite=False,
                        progress_callback=None, clean_metadata=True, delete_videos_after=False):
    """
    Convert all video files in a folder to MP3
    
    Args:
        input_folder: Folder containing video files
        output_folder: Output folder for MP3 files (default: same as input)
        quality: Audio quality/bitrate
        recursive: Whether to search subdirectories
        preserve_metadata: Whether to preserve metadata from videos
        overwrite: Whether to overwrite existing MP3 files
        progress_callback: Callback function for progress updates
        clean_metadata: Whether to filter out video-specific metadata
        delete_videos_after: Whether to move videos to trash after successful conversion
        
    Returns:
        Dictionary with conversion statistics
    """
    input_folder = os.path.normpath(os.path.expanduser(input_folder))
    if not os.path.isdir(input_folder):
        raise ValueError(f"Input folder does not exist: {input_folder}")
    
    if output_folder:
        output_folder = os.path.normpath(os.path.expanduser(output_folder))
        os.makedirs(output_folder, exist_ok=True)
    
    # Find video files
    video_files = []
    if recursive:
        for root, _, files in os.walk(input_folder):
            for file in files:
                if is_video_file(file):
                    video_files.append(os.path.join(root, file))
    else:
        for file in os.listdir(input_folder):
            filepath = os.path.join(input_folder, file)
            if os.path.isfile(filepath) and is_video_file(file):
                video_files.append(filepath)
    
    if not video_files:
        raise ValueError("No video files found in the input folder")
    
    stats = {
        'total': len(video_files),
        'converted': 0,
        'skipped': 0,
        'failed': 0,
        'deleted': 0  # New stat for deleted videos
    }
    
    for i, video_path in enumerate(video_files):
        try:
            # Determine output path
            if output_folder:
                # Maintain folder structure in output
                rel_path = os.path.relpath(video_path, input_folder)
                rel_dir = os.path.dirname(rel_path)
                video_name = os.path.splitext(os.path.basename(rel_path))[0]
                
                output_dir = os.path.join(output_folder, rel_dir)
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, f"{video_name}.mp3")
            else:
                output_path = None  # Will be generated in same directory
            
            # Convert video
            result_path = convert_video_to_mp3(
                video_path, output_path, quality, 
                preserve_metadata, overwrite, progress_callback, 
                clean_metadata, delete_videos_after
            )
            
            if result_path:
                stats['converted'] += 1
                # Check if video was actually deleted
                if delete_videos_after and not os.path.exists(video_path):
                    stats['deleted'] += 1
            else:
                stats['skipped'] += 1
                
        except Exception as e:
            stats['failed'] += 1
            if progress_callback:
                progress_callback(video_path, "Failed", str(e))
    
    return stats

def main():
    parser = argparse.ArgumentParser(description='Convert video files to MP3 using FFmpeg with auto-delete option')
    parser.add_argument('input', help='Input video file or folder')
    parser.add_argument('-o', '--output', help='Output file or folder (optional)')
    parser.add_argument('-q', '--quality', default='192k', 
                       help='Audio quality/bitrate (default: 192k)')
    parser.add_argument('-r', '--recursive', action='store_true',
                       help='Search subdirectories recursively')
    parser.add_argument('--no-metadata', action='store_true',
                       help='Do not preserve metadata from video files')
    parser.add_argument('--keep-video-metadata', action='store_true',
                       help='Keep video-specific metadata (not recommended)')
    parser.add_argument('--overwrite', action='store_true',
                       help='Overwrite existing output files')
    parser.add_argument('--delete-videos', action='store_true',
                       help='Move video files to trash after successful conversion')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    # Check if FFmpeg is available
    if not check_ffmpeg():
        print("Error: FFmpeg not found. Please install FFmpeg and ensure it's in your PATH.")
        print("Visit https://ffmpeg.org/download.html for installation instructions.")
        return 1
    
    # Show warning if delete option is used
    if args.delete_videos:
        print("WARNING: Video files will be moved to trash after successful conversion.")
        response = input("Are you sure you want to continue? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            print("Operation cancelled.")
            return 0
    
    input_path = os.path.normpath(os.path.expanduser(args.input))
    
    def progress_callback(file_path, status, details):
        if args.verbose:
            filename = os.path.basename(file_path)
            print(f"{status}: {filename} - {details}")
    
    try:
        if os.path.isfile(input_path):
            # Single file conversion
            if not is_video_file(input_path):
                print(f"Error: Not a supported video file: {input_path}")
                return 1
            
            output_path = args.output
            result = convert_video_to_mp3(
                input_path, output_path, args.quality,
                not args.no_metadata, args.overwrite, progress_callback,
                not args.keep_video_metadata,  # clean_metadata
                args.delete_videos  # delete_video_after
            )
            
            if result:
                print(f"Successfully converted: {result}")
                if args.delete_videos and not os.path.exists(input_path):
                    print("Video file moved to trash.")
            else:
                print("Conversion skipped (file already exists)")
                
        elif os.path.isdir(input_path):
            # Batch conversion
            stats = batch_convert_videos(
                input_path, args.output, args.quality,
                args.recursive, not args.no_metadata, args.overwrite,
                progress_callback, not args.keep_video_metadata,  # clean_metadata
                args.delete_videos  # delete_videos_after
            )
            
            print(f"\nConversion complete:")
            print(f"Total files: {stats['total']}")
            print(f"Converted: {stats['converted']}")
            print(f"Skipped: {stats['skipped']}")
            print(f"Failed: {stats['failed']}")
            if args.delete_videos:
                print(f"Videos moved to trash: {stats['deleted']}")
            
        else:
            print(f"Error: Input path does not exist: {input_path}")
            return 1
            
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())