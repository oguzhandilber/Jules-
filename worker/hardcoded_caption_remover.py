import cv2
import numpy as np
import os
import subprocess
import time
import uuid # For temporary filenames

# Placeholder for actual model loading and device selection
EAST_MODEL_LOADED = False
LAMA_MODEL_LOADED = False
DEVICE = "cpu"

def load_east_detector(model_path):
    global EAST_MODEL_LOADED
    print(f"Placeholder: Attempting to load EAST model from {model_path}")
    #EAST_MODEL_LOADED = cv2.dnn.readNet(model_path) # Actual line
    EAST_MODEL_LOADED = True # Placeholder
    return EAST_MODEL_LOADED

def detect_text_regions_placeholder(frame, east_detector_is_loaded, min_confidence=0.7, frame_width=320, frame_height=320):
    if not east_detector_is_loaded: # Pass the loaded status/model itself
        print("EAST model not loaded (placeholder).")
        return []

    if np.any(frame):
        h, w = frame.shape[:2]
        box_h = h // 10
        box_y = h - box_h - (h // 20)
        # Format: (x_start, y_start, x_end, y_end) - common for some detectors
        # For create_mask_from_boxes, we'll convert to (x,y,width,height) if needed or use as is
        # Let's use (x,y,width,height) for consistency with cv2.rectangle
        rect_x = w // 10
        rect_y = box_y
        rect_w = w - (2 * (w // 10))
        rect_h = box_h
        # print(f"Placeholder: Detected dummy text box: {(rect_x, rect_y, rect_w, rect_h)}")
        return [(rect_x, rect_y, rect_w, rect_h)]
    return []

def load_lama_model(config_path, model_path):
    global LAMA_MODEL_LOADED
    print(f"Placeholder: Attempting to load LaMa model from {config_path} & {model_path}")
    LAMA_MODEL_LOADED = True # Placeholder
    return LAMA_MODEL_LOADED

def inpaint_frame_placeholder(frame, mask, lama_model_is_loaded, device):
    if not lama_model_is_loaded: # Pass the loaded status/model
        print("LaMa model not loaded (placeholder).")
        return frame

    inpainted_frame = frame.copy()
    if mask is not None and np.any(mask):
        # Simple inpainting: fill mask region with a color (e.g., black or average color)
        # For black:
        inpainted_frame[mask == 255] = [0, 0, 0]
        # print("Placeholder: Applied dummy inpainting (black fill).")
    return inpainted_frame

def create_mask_from_boxes(frame_shape, boxes):
    mask = np.zeros((frame_shape[0], frame_shape[1]), dtype=np.uint8)
    for (x, y, w, h) in boxes:
        # Ensure box coordinates are within frame boundaries before drawing
        # Add some padding to the mask if desired
        padding = 5 # pixels
        x_start = max(0, x - padding)
        y_start = max(0, y - padding)
        x_end = min(frame_shape[1], x + w + padding)
        y_end = min(frame_shape[0], y + h + padding)
        cv2.rectangle(mask, (x_start, y_start), (x_end, y_end), (255), -1)
    return mask

def process_video_hardcoded_internal(input_filepath, output_filepath_final):
    global EAST_MODEL_LOADED, LAMA_MODEL_LOADED # Ensure global scope for model loaded flags

    # Models should ideally be loaded by the worker process once on startup, not per job.
    # This is a simplified placeholder.
    if not EAST_MODEL_LOADED:
        load_east_detector("models/frozen_east_text_detection.pb") # Path is placeholder
    if not LAMA_MODEL_LOADED:
        load_lama_model("models/lama_config.yaml", "models/big-lama.pt") # Paths are placeholders

    if not os.path.exists(input_filepath):
        return False, f"Input file not found: {input_filepath}"

    cap = cv2.VideoCapture(input_filepath)
    if not cap.isOpened():
        return False, f"Could not open video file: {input_filepath}"

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    if fps == 0 or frame_width == 0 or frame_height == 0:
        cap.release()
        return False, f"Video properties (fps, width, height) are zero for {input_filepath}. Cannot process."

    temp_id = str(uuid.uuid4())
    # Ensure temp files are in a writable directory, e.g., same as output_filepath_final
    temp_dir = os.path.dirname(output_filepath_final)
    os.makedirs(temp_dir, exist_ok=True) # Ensure temp_dir (which is PROCESSED_FOLDER) exists

    temp_audio_path = os.path.join(temp_dir, f"temp_audio_{temp_id}.aac")
    temp_video_no_audio_path = os.path.join(temp_dir, f"temp_video_no_audio_{temp_id}.mp4")

    audio_extracted_successfully = False
    try:
        audio_extract_cmd = ['ffmpeg', '-i', input_filepath, '-vn', '-acodec', 'copy', '-y', temp_audio_path]
        subprocess.run(audio_extract_cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(temp_audio_path) and os.path.getsize(temp_audio_path) > 0:
            audio_extracted_successfully = True
            print("Audio extracted.")
        else:
            print("No audio stream or error during extraction.")
    except Exception as e:
        print(f"Audio extraction error: {e}. Proceeding without audio.")

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out_temp_video = cv2.VideoWriter(temp_video_no_audio_path, fourcc, fps, (frame_width, frame_height))

    frame_count = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break
        frame_count += 1
        # if frame_count % int(fps if fps > 0 else 30) == 0: print(f"Frame {frame_count}...") # Log less

        boxes = detect_text_regions_placeholder(frame, EAST_MODEL_LOADED)
        processed_frame = frame
        if boxes:
            mask = create_mask_from_boxes(frame.shape, boxes)
            processed_frame = inpaint_frame_placeholder(frame, mask, LAMA_MODEL_LOADED, DEVICE)
        out_temp_video.write(processed_frame)

    cap.release()
    out_temp_video.release()
    print(f"Processed {frame_count} frames to {temp_video_no_audio_path}")

    final_video_success = False
    reintegration_cmd_list = [] # For logging
    try:
        if audio_extracted_successfully:
            reintegration_cmd_list = [
                'ffmpeg', '-i', temp_video_no_audio_path, '-i', temp_audio_path,
                '-c:v', 'copy', '-c:a', 'aac', '-strict', 'experimental',
                '-map', '0:v:0', '-map', '1:a:0', '-shortest', '-y', output_filepath_final
            ]
        else:
             reintegration_cmd_list = [
                'ffmpeg', '-i', temp_video_no_audio_path,
                '-c:v', 'copy', '-an', '-y', output_filepath_final
            ]
        print(f"Running ffmpeg for final output: {' '.join(reintegration_cmd_list)}")
        result = subprocess.run(reintegration_cmd_list, check=True, capture_output=True, text=True)
        final_video_success = True
    except subprocess.CalledProcessError as e:
        print(f"Audio reintegration error: {e.stderr}")
        # Fallback logic
        if os.path.exists(temp_video_no_audio_path) and os.path.getsize(temp_video_no_audio_path) > 0:
            os.rename(temp_video_no_audio_path, output_filepath_final)
            return True, f"Processed video (audio error, video only): {output_filepath_final}"
        return False, f"Audio reintegration failed. FFmpeg error: {e.stderr}"
    except Exception as e:
        return False, f"General audio reintegration error: {str(e)}"
    finally:
        if os.path.exists(temp_audio_path): os.remove(temp_audio_path)
        # Only remove temp_video_no_audio_path if reintegration was successful OR if it was successfully renamed in fallback
        if final_video_success or (not os.path.exists(temp_video_no_audio_path) and os.path.exists(output_filepath_final)):
            if os.path.exists(temp_video_no_audio_path): os.remove(temp_video_no_audio_path)
        else:
             print(f"Warning: Temp video {temp_video_no_audio_path} kept due to potential reintegration failure and no fallback success.")


    if final_video_success and os.path.exists(output_filepath_final) and os.path.getsize(output_filepath_final) > 0:
        return True, f"Successfully processed (hardcoded captions - placeholder): {output_filepath_final}"
    else:
        return False, f"Processing failed or output file is empty/missing. Last command: {' '.join(reintegration_cmd_list)}"

def remove_hardcoded_captions(input_filepath, output_filepath):
    success = False; message = ""
    try:
        print(f"Starting hardcoded caption removal for: {input_filepath}")
        success, message = process_video_hardcoded_internal(input_filepath, output_filepath)
    except Exception as e:
        message = f"Critical error in remove_hardcoded_captions for {input_filepath}: {str(e)}"
        print(message) # Log it
        success = False
    finally:
        if os.path.exists(input_filepath):
            try:
                os.remove(input_filepath)
                print(f"Cleaned original input: {input_filepath}")
            except Exception as e_remove:
                print(f"Error cleaning input {input_filepath}: {e_remove}")
    return success, message

if __name__ == '__main__':
    print("--- Direct test of hardcoded_caption_remover.py ---")
    # Create dummy folders in a temporary location (e.g., /tmp or relative to script if permissions allow)
    # For consistency with how RQ worker might run, let's use relative paths.
    # The worker will be started from project root, so paths like '../uploads' are relative to that.
    # This direct test will run from worker/ directory.
    # So, paths should be relative to worker/ or use absolute paths for testing.

    # Base path for test data, relative to the script's location (worker/)
    test_base_dir = os.path.join(os.path.dirname(__file__), "test_data_hardcoded")
    test_uploads_dir = os.path.join(test_base_dir, "uploads")
    test_processed_dir = os.path.join(test_base_dir, "processed_videos")

    os.makedirs(test_uploads_dir, exist_ok=True)
    os.makedirs(test_processed_dir, exist_ok=True)

    dummy_input_vid = os.path.join(test_uploads_dir, "sample_hardcoded_test.mp4")
    dummy_output_vid = os.path.join(test_processed_dir, "sample_hardcoded_test_processed.mp4")

    ffmpeg_gen_cmd = [
        'ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=c=blue:s=320x240:d=2',
        '-vf', "drawtext=text='Test Caption':x=10:y=H-th-10:fontcolor=white:fontsize=24",
        '-t', '2', dummy_input_vid
    ]
    try:
        print(f"Generating dummy input: {' '.join(ffmpeg_gen_cmd)}")
        subprocess.run(ffmpeg_gen_cmd, check=True, capture_output=True, text=True)
        print(f"Dummy input created: {dummy_input_vid}")

        success, message = remove_hardcoded_captions(dummy_input_vid, dummy_output_vid)

        if success: print(f"Direct test SUCCEEDED. Msg: {message}")
        else: print(f"Direct test FAILED. Msg: {message}")

        if os.path.exists(dummy_output_vid): print(f"Output at: {dummy_output_vid}")
        else: print("Output file not found after processing attempt.")

    except FileNotFoundError: print("FFmpeg not found. Cannot run direct test.")
    except subprocess.CalledProcessError as e: print(f"FFmpeg gen failed: {e.stderr}")
    except Exception as e: print(f"Error in direct test: {e}")
    finally:
        # Cleanup: input should be auto-deleted by the function.
        # if os.path.exists(dummy_input_vid): os.remove(dummy_input_vid)
        if os.path.exists(dummy_output_vid): os.remove(dummy_output_vid)
        # Clean up directories if they were created by this test specifically
        # For simplicity, we'll leave them if other tests might use them.
        # if os.path.exists(test_uploads_dir): os.rmdir(test_uploads_dir)
        # if os.path.exists(test_processed_dir): os.rmdir(test_processed_dir)
        # if os.path.exists(test_base_dir) and not os.listdir(test_base_dir): os.rmdir(test_base_dir)
        print("--- Direct test finished ---")
