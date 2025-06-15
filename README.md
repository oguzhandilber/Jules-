# Clarity - Video Caption Remover

A web application to remove captions from videos.

## Features (Updated for Milestone 5 / Hardcoded Captions)

*   **Soft Subtitle Removal:**
    *   Removes embedded subtitle tracks (e.g., SRT, ASS, VTT) from video containers (MP4, MKV, MOV).
    *   Fast operation, as it's a stream copy (no re-encoding of video/audio).
*   **Hardcoded Caption Removal (Experimental - Milestone 5):**
    *   Aims to remove burned-in/hardcoded text directly from video frames.
    *   Uses a pipeline involving (currently placeholder) Machine Learning models:
        *   **Text Detection:** Placeholder for OpenCV with EAST (Efficient and Accurate Scene Text Detector).
        *   **Video Inpainting:** Placeholder for an advanced model like LaMa (Large Mask Inpainting) for frame-by-frame inpainting.
    *   **Performance:** This process is computationally intensive and significantly slower than soft subtitle removal. GPU acceleration is strongly recommended for the worker processing these jobs.
    *   **Status:** The video processing pipeline (frame extraction, audio handling, video reconstruction) is implemented. The core ML model inference logic for text detection and inpainting within  uses placeholder functions that simulate the process without actual ML inference.
*   **Asynchronous Processing:** Uses Redis and RQ (Redis Queue) for background task processing, keeping the UI responsive.
    *   Separate queues ('default' for soft, 'hard_caption_queue' for hardcoded) allow for dedicated workers.
*   **Email Notifications (Optional for Hardcoded Removal):** Users can provide an email address to be notified upon completion or failure of (long-running) hardcoded caption removal tasks. (Email sending is currently simulated).
*   **File Metadata and Cleanup:** Tracks uploaded/processed files and implements a deletion policy (details in Privacy Policy).

## Usage (Updated for Milestone 5)

1.  Navigate to the web interface (default:  if using Docker).
2.  Select the video file you want to process.
3.  Choose the type of caption removal:
    *   **Soft Subtitles:** For embedded, non-visible-in-frame text tracks. (Fast)
    *   **Hardcoded Captions:** For text that is visibly part of the video image. (Slow, Experimental, GPU Recommended)
4.  If you select "Hardcoded Captions", you may optionally provide your email address to receive a notification.
5.  Click "Upload and Process".
6.  The UI will show the job status by polling the backend. For long-running hardcoded jobs, the email notification (if provided) will also inform you of completion or failure.
7.  Once processing is complete and successful, a download link for the processed video will appear.

## Technical Setup & Developer Notes (Updated for Milestone 5)

The application is containerized using Docker and Docker Compose.

*   **Services:** Frontend (Nginx), Backend (Flask), Redis, RQ Worker (for 'default' queue - soft subtitles), RQ Worker (for 'hard_caption_queue' - hardcoded captions).
*   **ML Models for Hardcoded Captions:**
    *   The hardcoded caption removal worker () is designed to use pre-trained model files. Placeholder text files indicating where to place the actual models are in the `models/` directory:
        *    (for EAST text detector)
        *    (for LaMa inpainting model checkpoint)
        *    (if a config YAML is used by the LaMa implementation)
    *   **Important:** The actual Python code to load and run these models in  currently uses **placeholder functions**. Real ML inference logic needs to be implemented.
*   **RQ Queues:**
    *   : For soft subtitle removal jobs (processed by ).
    *   : For hardcoded caption removal jobs (can be processed by  or a similarly configured worker).
*   **GPU Worker Setup (Conceptual for M5):**
    *   The  is provided as a starting point for a worker that might handle GPU-intensive tasks.
    *   To enable GPU processing, the  (or a new ) would need to use an NVIDIA CUDA base image and install GPU-enabled versions of ML libraries (e.g., PyTorch with CUDA).
    *   The  would then need to be configured to build this GPU-enabled worker image and potentially request GPU resources from the host (using Docker's GPU support features).

## File Deletion Policy

Uploaded and processed files are managed by an automated deletion policy, tracked via  (which is gitignored).
*   Original uploaded files are deleted by the respective worker task after processing (successful or failed).
*   Processed (caption-removed) video files are deleted from the server by the  (intended to be run periodically, e.g., via cron) based on the following rules:
    *   24 hours after the original upload time, OR
    *   1 hour after the file is first downloaded.
*   Whichever condition occurs first triggers the deletion. See the Privacy Policy page on the application for more details.

## Limitations (Updated for Milestone 5)

*   **Hardcoded Caption Removal Quality:** The effectiveness of hardcoded caption removal is entirely dependent on the actual ML models used for text detection and video inpainting. The current implementation uses **placeholder logic** for these critical ML components.
*   **Performance of Hardcoded Removal:** Real ML models for this task are computationally expensive. The current placeholder logic is fast but does not perform actual ML. With real models, CPU processing would be extremely slow. GPU acceleration (via a dedicated GPU worker) is essential for practical performance.
*   **Temporal Consistency (Hardcoded Inpainting):** Advanced video inpainting models often consider temporal consistency across frames. The placeholder (and many simpler frame-by-frame image inpainting models like LaMa) might not fully address this, potentially leading to flickering or artifacts in the inpainted regions of the output video.
*   **Email Delivery:** Email sending for notifications is currently **simulated** (prints to console/log in ). Requires configuration with actual SMTP server details for real email delivery.
*   **Error Handling & Robustness:** While basic error handling is in place, a production system would require more comprehensive error tracking, retries for transient issues (e.g., network blips with Redis), and more detailed logging.
