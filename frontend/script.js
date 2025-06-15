document.addEventListener('DOMContentLoaded', () => {
    const videoFileInput = document.getElementById('videoFile');
    const uploadButton = document.getElementById('uploadButton');
    const statusMessage = document.getElementById('statusMessage');
    const emailSection = document.getElementById('emailSection');
    const userEmailInput = document.getElementById('userEmail');
    const removalTypeRadios = document.querySelectorAll('input[name="removal_type"]');

    let dlAnchor = document.getElementById('downloadLinkAnchor');
    if (!dlAnchor) {
        dlAnchor = document.createElement('a');
        dlAnchor.id = 'downloadLinkAnchor';
        dlAnchor.style.display = 'none';
        dlAnchor.textContent = 'Download Processed Video';
        if (statusMessage && statusMessage.parentNode) {
             statusMessage.parentNode.insertBefore(dlAnchor, statusMessage.nextSibling);
        } else if (uploadButton && uploadButton.parentNode) { // Fallback
             uploadButton.parentNode.insertBefore(dlAnchor, uploadButton.nextSibling);
        }
    }

    function toggleEmailSection() {
        const selectedType = document.querySelector('input[name="removal_type"]:checked').value;
        if (selectedType === 'hard') {
            emailSection.style.display = 'block';
        } else {
            emailSection.style.display = 'none';
        }
    }
    removalTypeRadios.forEach(radio => radio.addEventListener('change', toggleEmailSection));
    toggleEmailSection(); // Initial check on page load

    uploadButton.addEventListener('click', async () => {
        const file = videoFileInput.files[0];
        if (!file) {
            statusMessage.textContent = 'Please select a video file first.';
            return;
        }

        const removalType = document.querySelector('input[name="removal_type"]:checked').value;
        const userEmail = userEmailInput.value;

        statusMessage.textContent = 'Uploading...';
        if (removalType === 'hard') {
            statusMessage.textContent = 'Uploading... (Hardcoded caption removal may take a very long time)';
        }

        uploadButton.disabled = true;
        dlAnchor.style.display = 'none';

        const formData = new FormData();
        formData.append('file', file);
        formData.append('removal_type', removalType);
        if (removalType === 'hard' && userEmail && userEmail.trim() !== '') { // Send email only if provided
            formData.append('user_email', userEmail.trim());
        }

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
                let queueMsg = removalType === 'hard' ? ' (long process)' : '';
                statusMessage.textContent = `File queued for processing${queueMsg}. Job ID: ${uploadResult.job_id}. Checking status...`;
                pollJobStatus(uploadResult.job_id);
            } else {
                statusMessage.textContent = 'Upload successful, but no Job ID received.';
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
            if (!statusResponse.headers.get("content-type") || !statusResponse.headers.get("content-type").includes("application/json")) {
                statusMessage.textContent = `Error fetching status: Server returned non-JSON (${statusResponse.status} ${statusResponse.statusText})`;
                setTimeout(() => pollJobStatus(jobId), 10000);
                return;
            }
            const statusResult = await statusResponse.json();

            if (!statusResponse.ok) {
                statusMessage.textContent = `Error fetching status for ${jobId}: ${statusResult.error || statusResponse.statusText || 'Unknown server error'}`;
                if (statusResponse.status === 404) {
                    uploadButton.disabled = false;
                    return;
                }
                setTimeout(() => pollJobStatus(jobId), 5000);
                return;
            }

            let currentStatus = statusResult.status;
            let jobMeta = statusResult.meta || {}; // Ensure meta exists
            let removalTypeInfo = jobMeta.removal_type || (statusResult.queue_name && statusResult.queue_name.includes('hard') ? 'hard' : 'soft');

            statusMessage.textContent = `Job ${jobId} (${removalTypeInfo}) Status: ${currentStatus}`;
            if (currentStatus === 'queued' && removalTypeInfo === 'hard') {
                 statusMessage.textContent += ` (This may take many minutes to hours. If you provided an email, you'll be notified upon completion.)`;
            } else if (currentStatus === 'started' && removalTypeInfo === 'hard') {
                 statusMessage.textContent += ` (Processing in progress...)`;
            }


            if (currentStatus === 'finished') {
                if (statusResult.result && statusResult.result.success) {
                    statusMessage.textContent = `Job ${jobId} (${removalTypeInfo}) processing complete!`;
                    let processedFileName = statusResult.result.processed_file_name;
                    let downloadUrl = statusResult.result.download_url; // Expecting this from backend
                    if (processedFileName && downloadUrl) {
                        dlAnchor.href = downloadUrl;
                        dlAnchor.download = processedFileName;
                        dlAnchor.style.display = 'block';
                        statusMessage.textContent += ` Ready for download.`;
                    } else {
                        statusMessage.textContent = `Job ${jobId} (${removalTypeInfo}) complete, but download information is missing.`;
                    }
                } else { // Job finished but was not successful
                    statusMessage.textContent = `Job ${jobId} (${removalTypeInfo}) processing failed: ${statusResult.result ? (statusResult.result.message || statusResult.result.message_or_path) : (statusResult.error_message || 'Unknown error')}`;
                }
                uploadButton.disabled = false;
            } else if (currentStatus === 'failed') {
                statusMessage.textContent = `Job ${jobId} (${removalTypeInfo}) processing failed: ${statusResult.error_message || 'Unknown error from job failure'}`;
                uploadButton.disabled = false;
            } else { // e.g. queued, started, deferred
                setTimeout(() => pollJobStatus(jobId), 3000);
            }
        } catch (error) {
            statusMessage.textContent = `Error polling status for ${jobId}: ${error.message}`;
            setTimeout(() => pollJobStatus(jobId), 5000);
        }
    }
});
