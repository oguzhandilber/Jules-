import os
import sys
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import redis
from rq import Queue as RQ_Queue

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

app = Flask(__name__)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, 'uploads')
PROCESSED_FOLDER = os.path.join(PROJECT_ROOT, 'processed_videos')
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'mkv', 'avi', 'webm'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
redis_conn = None
try:
    redis_conn = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    redis_conn.ping()
    print(f"Backend successfully connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
except redis.exceptions.ConnectionError as e_redis_conn:
    print(f"Backend FATAL ERROR: Could not connect to Redis at {REDIS_HOST}:{REDIS_PORT}. RQ will not work. Error: {e_redis_conn}")
    # redis_conn remains None

rq_queue = None
if redis_conn:
    rq_queue = RQ_Queue('default', connection=redis_conn)
else:
    print("RQ Queue not initialized due to Redis connection failure.")


def allowed_file(filename):
    return '.' in filename and            filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_file_route():
    if not rq_queue: # Check if rq_queue was initialized
        return jsonify({'error': 'Backend not connected to Redis or RQ queue not initialized, service unavailable.'}), 503

    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        original_filename = secure_filename(file.filename)
        input_filepath = os.path.join(app.config['UPLOAD_FOLDER'], original_filename)

        name, ext = os.path.splitext(original_filename)
        processed_filename_expected = f"{name}_no_subs{ext}"
        output_filepath = os.path.join(app.config['PROCESSED_FOLDER'], processed_filename_expected)

        try:
            file.save(input_filepath)

            job = rq_queue.enqueue(
                'worker.soft_subtitle_remover.remove_soft_subtitles',
                args=(input_filepath, output_filepath),
                job_timeout='1h',
                meta={'original_filename': original_filename, 'expected_processed_filename': processed_filename_expected}
            )

            return jsonify({
                'message': 'File uploaded and queued for processing.',
                'job_id': job.id
            }), 202

        except Exception as e:
            # Basic cleanup if file was saved before error
            if os.path.exists(input_filepath) and 'job' not in locals():
                 os.remove(input_filepath)
            app.logger.error(f"Error during upload/queueing: {str(e)}", exc_info=True) # Log detailed error
            return jsonify({'error': f'An unexpected error occurred during upload or queueing process.'}), 500 # Generic message

    else:
        return jsonify({'error': 'File type not allowed'}), 400

@app.route('/status/<job_id>', methods=['GET'])
def job_status_route(job_id):
    if not rq_queue: # Check if rq_queue was initialized
        return jsonify({'error': 'Backend not connected to Redis or RQ queue not initialized, service unavailable.'}), 503

    try:
        job = rq_queue.fetch_job(job_id)
    except redis.exceptions.RedisError as e_redis_fetch: # More specific Redis error
        app.logger.error(f"Redis error fetching job {job_id}: {str(e_redis_fetch)}", exc_info=True)
        return jsonify({'error': f'Could not connect to Redis or fetch job status.'}), 500
    except Exception as e_fetch: # General fetch error
        app.logger.error(f"General error fetching job {job_id}: {str(e_fetch)}", exc_info=True)
        return jsonify({'error': f'Could not fetch job status due to an unexpected error.'}), 500

    if job is None:
        return jsonify({'error': 'Job not found'}), 404

    response_data = {
        'job_id': job.id,
        'status': job.get_status(),
        'enqueued_at': job.enqueued_at.isoformat() if job.enqueued_at else None,
        'started_at': job.started_at.isoformat() if job.started_at else None,
        'ended_at': job.ended_at.isoformat() if job.ended_at else None,
    }

    if job.is_finished:
        job_success, message_from_worker = job.result
        processed_file_name_actual = ""
        final_success_flag = job_success

        if job_success:
            if job.meta and job.meta.get('expected_processed_filename'):
                processed_file_name_actual = job.meta['expected_processed_filename']
            elif isinstance(message_from_worker, str) and ': ' in message_from_worker:
                full_path = message_from_worker.split(': ')[-1]
                processed_file_name_actual = os.path.basename(full_path)

            if not processed_file_name_actual:
                message_from_worker = "Processing reported success, but processed filename could not be determined."
                final_success_flag = False

        download_url = None
        if final_success_flag and processed_file_name_actual:
            download_url = f"/download/{processed_file_name_actual}"

        response_data['result'] = {
            'success': final_success_flag,
            'message': message_from_worker,
            'processed_file_name': processed_file_name_actual if final_success_flag else None,
            'download_url': download_url
        }
    elif job.is_failed:
        app.logger.error(f"Job {job_id} failed. Traceback: {job.exc_info}")
        response_data['error_message'] = "Processing failed due to an internal error. Please try again later."
        response_data['error_reference'] = job.id

    return jsonify(response_data), 200

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    try:
        if not filename or '/' in filename or '..' in filename:
             return jsonify({'error': 'Invalid filename.'}), 400
        return send_from_directory(app.config['PROCESSED_FOLDER'], filename, as_attachment=True)
    except FileNotFoundError:
        return jsonify({'error': 'File not found.'}), 404
    except Exception as e:
        app.logger.error(f"Error during download of {filename}: {str(e)}", exc_info=True)
        return jsonify({'error': f'Error during download.'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
