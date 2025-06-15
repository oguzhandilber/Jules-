import os, sys
from flask import Flask, request, jsonify, send_from_directory, url_for
from werkzeug.utils import secure_filename
import redis
from rq import Queue as RQ_Queue
from metadata_manager import add_file_record, update_job_status_in_metadata, record_download
from email_sender import send_email
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
app = Flask(__name__)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, 'uploads'); PROCESSED_FOLDER = os.path.join(PROJECT_ROOT, 'processed_videos')
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'mkv', 'avi', 'webm'}
app.config.update(UPLOAD_FOLDER=UPLOAD_FOLDER, PROCESSED_FOLDER=PROCESSED_FOLDER, SERVER_NAME=os.getenv('FLASK_SERVER_NAME','localhost:5000'))
os.makedirs(UPLOAD_FOLDER, exist_ok=True); os.makedirs(PROCESSED_FOLDER, exist_ok=True)
REDIS_HOST=os.getenv('REDIS_HOST','127.0.0.1'); REDIS_PORT=int(os.getenv('REDIS_PORT',6379)); redis_conn=None
try:
    redis_conn=redis.Redis(host=REDIS_HOST,port=REDIS_PORT,decode_responses=True,socket_connect_timeout=2); redis_conn.ping()
    app.logger.info(f"Redis connected: {REDIS_HOST}:{REDIS_PORT}")
except redis.exceptions.ConnectionError as e: app.logger.error(f"Redis connection error: {e}")
default_rq_queue=None; hard_caption_rq_queue=None
if redis_conn:
    default_rq_queue=RQ_Queue('default',connection=redis_conn); hard_caption_rq_queue=RQ_Queue('hard_caption_queue',connection=redis_conn)
    app.logger.info("RQ queues initialized.")
else: app.logger.warning("RQ Queues NOT initialized (Redis connection failed).")
def allowed_file(fn): return '.' in fn and fn.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS
@app.route('/upload', methods=['POST'])
def upload_file_route(): # Full version from M5-Step6
    if not redis_conn: app.logger.error("Upload failed: No Redis connection."); return jsonify({'error': 'Service unavailable (Queue system offline - Redis connection).'}),503
    rt=request.form.get('removal_type','soft').lower(); tq=hard_caption_rq_queue if rt=='hard' else default_rq_queue
    if not tq: app.logger.error(f"Queue for {rt} unavailable."); return jsonify({'error':f'Service for {rt} unavailable (Queue setup issue).'}),503
    if 'file' not in request.files: return jsonify({'error':'No file part'}),400
    f=request.files['file']; ue=request.form.get('user_email') if rt=='hard' else None
    if f.filename=='': return jsonify({'error':'No selected file'}),400
    if f and allowed_file(f.filename):
        ofn=secure_filename(f.filename); ifp=os.path.join(app.config['UPLOAD_FOLDER'],ofn)
        n,e=os.path.splitext(ofn); pfn_exp=f"{n}_no_{rt}subs{e}"; ofp=os.path.join(app.config['PROCESSED_FOLDER'],pfn_exp)
        try:
            os.makedirs(app.config['UPLOAD_FOLDER'],exist_ok=True); f.save(ifp)
            m={'original_filename':ofn,'expected_processed_filename':pfn_exp,'removal_type':rt};
            if ue: m['user_email']=ue
            job_fn_path=f"worker.{'hardcoded' if rt=='hard' else 'soft'}_subtitle_remover.remove_{'hardcoded_captions' if rt=='hard' else 'soft_subtitles'}"
            job=tq.enqueue(job_fn_path,args=(ifp,ofp),job_timeout='3h' if rt=='hard' else '1h',meta=m)
            add_file_record(job.id,ofn,pfn_exp,rt,ue)
            return jsonify({'message':f'File queued ({rt}). Job ID: {job.id}'}),202
        except Exception as e:
            app.logger.error(f"Upload error ({rt}): {e}",exc_info=True)
            if os.path.exists(ifp) and 'job' not in locals():
                try: os.remove(ifp)
                except Exception as er: app.logger.error(f"Cleanup failed for {ifp} after upload error: {er}")
            if isinstance(e, redis.exceptions.RedisError): return jsonify({'error':'Service unavailable (Queue enqueue error).'}),503
            return jsonify({'error':'Upload/queueing error.'}),500
    app.logger.info(f"Upload rejected: File type not allowed for '{f.filename}'. Allowed: {ALLOWED_EXTENSIONS}")
    return jsonify({'error':'File type not allowed'}),400
@app.route('/status/<job_id>')
def job_status_route(job_id): # Full version from M5-Step6
    if not redis_conn: return jsonify({'error':'Queue system offline.'}), 503
    try: job = RQ_Queue.fetch_job(job_id, connection=redis_conn)
    except Exception as e: app.logger.error(f"Fetch job error {job_id}: {e}", exc_info=True); return jsonify({'error':'Fetch job error.'}), 500
    if not job: return jsonify({'error':'Job not found.'}), 404
    job_rq_status = job.get_status(); meta = job.meta or {}; resp = {'job_id': job.id, 'status': job_rq_status, 'queue_name': job.origin, 'meta': meta, 'enqueued_at': job.enqueued_at.isoformat() + 'Z' if job.enqueued_at else None, 'started_at': job.started_at.isoformat() + 'Z' if job.started_at else None, 'ended_at': job.ended_at.isoformat() + 'Z' if job.ended_at else None}
    meta_status_update = job_rq_status; worker_res_meta = None; email_sent = False
    if job.is_finished:
        s, msg = job.result; pfn = meta.get('expected_processed_filename') if s else None
        if s and not pfn and isinstance(msg, str) and ': ' in msg: pfn = os.path.basename(msg.split(': ')[-1])
        final_s = s and bool(pfn); final_msg = msg if final_s else (msg if not s else "Output filename error.")
        dl_url_email = None
        if final_s and pfn:
            with app.app_context(): dl_url_email = url_for('download_file_route', filename=pfn, _external=True)
        resp['result'] = {'success':final_s,'message':final_msg,'processed_file_name':pfn if final_s else None,'download_url': f"/download/{pfn}" if final_s and pfn else None}
        meta_status_update = 'completed' if final_s else 'failed_processing'; worker_res_meta = resp['result']
        user_email = meta.get('user_email')
        if user_email and meta.get('removal_type') == 'hard' and not meta.get('_email_sent_finished'):
            email_subject = f"Video Processing {'Complete' if final_s else 'Issue'} for {meta.get('original_filename', 'video')}"
            email_body = f"<p>Video '{meta.get('original_filename', 'N/A')}' status: {'Success' if final_s else 'Failed'}.</p><p>Details: {final_msg}</p>"
            if final_s and dl_url_email: email_body += f"<p>Download: <a href='{dl_url_email}'>{dl_url_email}</a></p>"
            send_email(user_email, email_subject, email_body); meta['_email_sent_finished'] = True; job.save_meta(); email_sent = True
    elif job.is_failed:
        app.logger.error(f"Job {job.id} (q: {job.origin}) failed: {job.exc_info}"); resp['error_message']="Internal error."; resp['error_reference'] = job.id
        meta_status_update = 'failed_rq_job'; worker_res_meta = {'success': False, 'message': resp['error_message']}
        user_email = meta.get('user_email')
        if user_email and meta.get('removal_type') == 'hard' and not meta.get('_email_sent_failed'):
            email_subject = f"Video Processing Failed for {meta.get('original_filename', 'video')}"
            email_body = f"<p>Processing for '{meta.get('original_filename', 'N/A')}' failed.</p><p>Error: {resp['error_message']}</p><p>Job ID: {job.id}.</p>"
            send_email(user_email, email_subject, email_body); meta['_email_sent_failed'] = True; job.save_meta(); email_sent = True
    if email_sent: app.logger.info(f"Email attempt for job {job.id} to {meta.get('user_email')}")
    updated_meta_rec = update_job_status_in_metadata(job_id, meta_status_update, worker_res_meta)
    if updated_meta_rec:
        for k_check in ['user_email', 'removal_type']:
            if resp.get('meta') and not resp['meta'].get(k_check) and updated_meta_rec.get(k_check): resp['meta'][k_check] = updated_meta_rec.get(k_check)
    return jsonify(resp), 200
@app.route('/download/<filename>')
def download_file_route(filename):
    if not filename or '/' in filename or '..' in filename: app.logger.warning(f"Invalid download: {filename}"); return jsonify({'error': 'Invalid filename.'}), 400
    try: record_download(filename); return send_from_directory(app.config['PROCESSED_FOLDER'], filename, as_attachment=True)
    except FileNotFoundError: app.logger.info(f"Download non-existent: {filename}"); return jsonify({'error': 'File not found.'}), 404
    except Exception as e: app.logger.error(f"Download error: {filename}: {e}", exc_info=True); return jsonify({'error': 'Download error.'}), 500
if __name__ == '__main__':
    if not app.debug:
        import logging; from logging.handlers import RotatingFileHandler; log_file = os.path.join(PROJECT_ROOT, 'app.log')
        fh = RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=3); fh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        fh.setLevel(logging.INFO); app.logger.addHandler(fh); app.logger.setLevel(logging.INFO); app.logger.info('Clarity Startup (Non-Debug)')
    else: app.logger.setLevel(logging.DEBUG); app.logger.info('Clarity Startup (Debug)')
    app.run(debug=True,host='0.0.0.0',port=5000)
