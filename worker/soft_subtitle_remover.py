import subprocess
import os

def remove_soft_subtitles(input_filepath, output_filepath):
    output_dir = os.path.dirname(output_filepath)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    ffmpeg_command = [
        'ffmpeg', '-i', input_filepath,
        '-c:v', 'copy', '-c:a', 'copy', '-sn',
        '-y', output_filepath
    ]

    try:
        print(f"Executing FFmpeg command: {' '.join(ffmpeg_command)}")
        result = subprocess.run(ffmpeg_command, capture_output=True, text=True, check=True)
        print(f"FFmpeg stdout: {result.stdout}")
        print(f"FFmpeg stderr: {result.stderr}")
        if os.path.exists(output_filepath) and os.path.getsize(output_filepath) > 0:
            message = f"Successfully removed subtitles: {output_filepath}"
            return True, message # Success
        else:
            message = f"FFmpeg ran, but output file is missing or empty. Stderr: {result.stderr}"
            return False, message # Failure
    except subprocess.CalledProcessError as e:
        message = f"Error during ffmpeg processing: {e.stderr}"
        print(message)
        return False, message # Failure
    except FileNotFoundError:
        message = "Error: ffmpeg command not found. Please ensure ffmpeg is installed."
        print(message)
        return False, message # Failure
    except Exception as e:
        message = f"An unexpected error occurred: {str(e)}"
        print(message)
        return False, message # Failure
    finally:
        # Cleanup the original uploaded file
        if os.path.exists(input_filepath):
            try:
                os.remove(input_filepath)
                print(f"Cleaned up original input file: {input_filepath}")
            except Exception as e_remove:
                print(f"Error cleaning up input file {input_filepath}: {str(e_remove)}")
        else:
            print(f"Input file {input_filepath} not found for cleanup (might have been moved or already deleted).")

if __name__ == '__main__':
    if not os.path.exists('../uploads'): os.makedirs('../uploads')
    if not os.path.exists('../processed_videos'): os.makedirs('../processed_videos')
    dummy_input_path = '../uploads/test_video_rq.mp4'
    with open(dummy_input_path, 'w') as f: f.write("dummy video data for direct test")
    dummy_output_path = '../processed_videos/test_video_rq_no_subs.mp4'
    print(f"Directly testing soft subtitle removal...")
    success, message = remove_soft_subtitles(dummy_input_path, dummy_output_path)
    if success: print(f"Direct test successful: {message}")
    else: print(f"Direct test failed: {message}")
    if os.path.exists(dummy_output_path): os.remove(dummy_output_path)
