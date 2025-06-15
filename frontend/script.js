document.addEventListener('DOMContentLoaded', () => {
    const videoFileInput = document.getElementById('videoFile');
    const uploadButton = document.getElementById('uploadButton');
    const statusMessage = document.getElementById('statusMessage');
    // const downloadLink = document.getElementById('downloadLink'); // This was a typo in prompt, not used.

    // Create download link element if it doesn't exist, and hide it.
    let dlAnchor = document.getElementById('downloadLinkAnchor');
    if (!dlAnchor) {
        dlAnchor = document.createElement('a');
        dlAnchor.id = 'downloadLinkAnchor';
        dlAnchor.style.display = 'none'; // Hide it initially
        dlAnchor.textContent = 'Download Processed Video';
        // Insert it after the status message or button
        // Ensure statusMessage exists before trying to insert.
        if (statusMessage) {
            statusMessage.parentNode.insertBefore(dlAnchor, statusMessage.nextSibling);
        } else if (uploadButton) { // Fallback to insert after upload button
            uploadButton.parentNode.insertBefore(dlAnchor, uploadButton.nextSibling);
        } else { // Fallback to append to body if critical elements are missing (should not happen in valid HTML)
            document.body.appendChild(dlAnchor);
        }
    }


    uploadButton.addEventListener('click', async () => {
        const file = videoFileInput.files[0];
        if (!file) {
            statusMessage.textContent = 'Please select a video file first.';
            return;
        }

        statusMessage.textContent = 'Uploading...';
        uploadButton.disabled = true;
        dlAnchor.style.display = 'none'; // Hide download link

        const formData = new FormData();
        formData.append('file', file);

        try {
            const uploadResponse = await fetch('/upload', {
                method: 'POST',
                body: formData,
            });

            const uploadResult = await uploadResponse.json();

            if (!uploadResponse.ok) {
                statusMessage.textContent = `Upload failed: ${uploadResult.error || uploadResponse.statusText || 'Server error'}`;
                uploadButton.disabled = false;
                return;
            }

            if (uploadResult.job_id) {
                statusMessage.textContent = 'File queued for processing. Checking status...';
                pollJobStatus(uploadResult.job_id);
            } else {
                // This case should ideally not happen if uploadResponse.ok is true and job_id is expected
                statusMessage.textContent = 'Upload successful, but no Job ID received. Cannot track processing.';
                uploadButton.disabled = false;
            }

        } catch (error) {
            statusMessage.textContent = `Upload request error: ${error.message}`;
            uploadButton.disabled = false;
        }
    });

    async function pollJobStatus(jobId) {
        try {
            const statusResponse = await fetch(`/status/${jobId}`);
            // Check for non-JSON responses first if server might return HTML error pages
            if (!statusResponse.headers.get("content-type") || !statusResponse.headers.get("content-type").includes("application/json")) {
                statusMessage.textContent = `Error fetching status: Server returned non-JSON response (${statusResponse.status} ${statusResponse.statusText})`;
                // Potentially stop polling or retry differently
                setTimeout(() => pollJobStatus(jobId), 10000); // Longer delay for server errors
                return;
            }

            const statusResult = await statusResponse.json();

            if (!statusResponse.ok) {
                statusMessage.textContent = `Error fetching status: ${statusResult.error || statusResponse.statusText || 'Unknown server error'}`;
                if (statusResponse.status === 404) {
                    uploadButton.disabled = false;
                    return; // Stop polling if job not found
                }
                setTimeout(() => pollJobStatus(jobId), 5000);
                return;
            }

            let currentStatus = statusResult.status;
            statusMessage.textContent = `Processing status: ${currentStatus}`;

            if (currentStatus === 'finished') {
                if (statusResult.result && statusResult.result.success) {
                    statusMessage.textContent = 'Processing complete!';

                    let processedFileName = statusResult.result.processed_file_name; // Expecting this from backend in M2

                    if (processedFileName) {
                        dlAnchor.href = `/download/${processedFileName}`;
                        dlAnchor.download = processedFileName;
                        dlAnchor.style.display = 'block';
                        statusMessage.textContent += ` Ready for download.`;
                    } else {
                        statusMessage.textContent = 'Processing complete, but could not determine download file name from response.';
                         // Log the problematic part of the response for debugging
                        console.error("Missing processed_file_name in statusResult.result:", statusResult.result);
                    }
                } else { // Job finished but was not successful
                    statusMessage.textContent = `Processing failed: ${statusResult.result ? statusResult.result.message_or_path : (statusResult.error_message || 'Unknown error')}`;
                }
                uploadButton.disabled = false;
            } else if (currentStatus === 'failed') {
                statusMessage.textContent = `Processing failed: ${statusResult.error_message || 'Unknown error from job failure'}`;
                uploadButton.disabled = false;
            } else { // Still processing
                setTimeout(() => pollJobStatus(jobId), 3000);
            }

        } catch (error) {
            statusMessage.textContent = `Error polling status: ${error.message}`;
            setTimeout(() => pollJobStatus(jobId), 5000); // Retry on network or unexpected errors
        }
    }
});
