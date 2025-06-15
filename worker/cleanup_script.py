import os
import sys
import datetime
import json
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from backend.metadata_manager import get_metadata_for_cleanup, mark_file_deleted_in_metadata, mark_file_failed_cleanup_in_metadata, load_metadata

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PROCESSED_FOLDER = os.path.join(PROJECT_ROOT, 'processed_videos')
UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, 'uploads')

DELETE_AFTER_UPLOAD_HOURS = 24
DELETE_AFTER_DOWNLOAD_HOURS = 1

def parse_iso_timestamp(ts_str):
    if not ts_str: return None
    try:
        if ts_str.endswith('Z'): ts_str = ts_str[:-1] + '+00:00'
        return datetime.datetime.fromisoformat(ts_str)
    except ValueError as e:
        print(f"Error parsing timestamp '{ts_str}': {e}")
        return None

def cleanup_files():
    print(f"{datetime.datetime.utcnow().isoformat()}Z - Starting cleanup process...")
    records_to_check = get_metadata_for_cleanup()
    now_utc = datetime.datetime.now(datetime.timezone.utc)

    if not records_to_check:
        print("No active file records found for cleanup.")
        return

    for record in records_to_check:
        job_id = record.get('job_id')
        status = record.get('status')
        processed_filename = record.get('processed_filename')
        original_filename = record.get('original_filename')

        if processed_filename and status == 'available_for_download':
            processed_filepath = os.path.join(PROCESSED_FOLDER, processed_filename)
            if not os.path.exists(processed_filepath):
                print(f"Job ID {job_id}: Processed file {processed_filepath} not found. Marking as deleted.")
                mark_file_deleted_in_metadata(job_id)
                continue

            upload_ts_str = record.get('upload_timestamp')
            upload_dt = parse_iso_timestamp(upload_ts_str)
            if upload_dt and (now_utc - upload_dt).total_seconds() >= DELETE_AFTER_UPLOAD_HOURS * 3600:
                print(f"Job ID {job_id}: Deleting processed {processed_filepath} (>{DELETE_AFTER_UPLOAD_HOURS}h since upload).")
                try:
                    os.remove(processed_filepath)
                    mark_file_deleted_in_metadata(job_id)
                except OSError as e:
                    mark_file_failed_cleanup_in_metadata(job_id)
                continue

            download_count = record.get('download_count', 0)
            first_download_ts_str = record.get('first_download_timestamp')
            if download_count > 0 and first_download_ts_str:
                first_download_dt = parse_iso_timestamp(first_download_ts_str)
                if first_download_dt and (now_utc - first_download_dt).total_seconds() >= DELETE_AFTER_DOWNLOAD_HOURS * 3600:
                    print(f"Job ID {job_id}: Deleting processed {processed_filepath} (>{DELETE_AFTER_DOWNLOAD_HOURS}h since first download).")
                    try:
                        os.remove(processed_filepath)
                        mark_file_deleted_in_metadata(job_id)
                    except OSError as e:
                        mark_file_failed_cleanup_in_metadata(job_id)
                    continue

        if original_filename and record.get('status') in ['failed_rq_job', 'failed_processing', 'queued', 'processing']:
            # Check age for queued/processing jobs to avoid deleting active uploads prematurely
            upload_ts_str = record.get('upload_timestamp')
            upload_dt = parse_iso_timestamp(upload_ts_str)
            is_stale_task = upload_dt and (now_utc - upload_dt).total_seconds() >= DELETE_AFTER_UPLOAD_HOURS * 3600 # e.g. if task stuck for 24h

            if record.get('status') in ['failed_rq_job', 'failed_processing'] or is_stale_task :
                original_filepath = os.path.join(UPLOAD_FOLDER, original_filename)
                if os.path.exists(original_filepath):
                    try:
                        print(f"Job ID {job_id}: Cleaning up original file {original_filepath} for {record.get('status')} job.")
                        os.remove(original_filepath)
                        # Original file cleanup is part of worker now, but this is a fallback.
                        # No separate metadata status for original file deletion by cleanup script.
                    except OSError as e:
                        print(f"Job ID {job_id}: Error cleaning original file {original_filepath}: {e}")

    current_metadata = load_metadata()
    deleted_count = sum(1 for r in current_metadata if r.get('status') == 'deleted')
    print(f"Cleanup process finished. Total records: {len(current_metadata)}, marked deleted: {deleted_count}.")

if __name__ == '__main__':
    cleanup_files()
