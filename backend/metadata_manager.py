import json, os, datetime, threading
METADATA_FILE = os.path.join(os.path.dirname(__file__), '..', 'file_metadata.json')
LOCK = threading.Lock()
def load_metadata():
    with LOCK:
        if not os.path.exists(METADATA_FILE): return []
        try:
            with open(METADATA_FILE, 'r') as f:
                c = f.read(); return json.loads(c) if c else []
        except (json.JSONDecodeError, IOError): return []
def save_metadata(d):
    with LOCK:
        with open(METADATA_FILE, 'w') as f: json.dump(d, f, indent=4)
def add_file_record(j, o, e, rt='soft', ue=None):
    m = load_metadata();
    m.append({"job_id": j, "original_filename": o, "processed_filename": None,
              "expected_processed_filename": e, "upload_timestamp": datetime.datetime.utcnow().isoformat() + 'Z',
              "status": "queued", "removal_type": rt, "user_email": ue, "download_count": 0,
              "first_download_timestamp": None, "worker_message": None})
    save_metadata(m)
def update_job_status_in_metadata(j, js, wr=None):
    m=load_metadata(); ur=None
    for r in m:
        if r['job_id']==j:
            r['status']=js
            if wr:
                r['worker_message']=str(wr.get('message', wr.get('message_or_path', 'N/A')))
                if js=='completed' and wr.get('success'):
                    r['processed_filename']=wr.get('processed_file_name'); r['status']='available_for_download'
                elif js=='completed' and not wr.get('success'): r['status']='failed_processing'
            ur=r; break
    if ur: save_metadata(m)
    return ur
def record_download(pfn):
    m=load_metadata(); u=False;
    for r in m:
        if r.get('processed_filename')==pfn and r['status']=='available_for_download':
            r['download_count']+=1;
            if r['first_download_timestamp'] is None: r['first_download_timestamp']=datetime.datetime.utcnow().isoformat()+'Z'
            u=True; break
    if u: save_metadata(m)
    return u
def get_metadata_for_cleanup(): return [r for r in load_metadata() if r.get('status') not in ['deleted', 'failed_cleanup']]
def mark_file_deleted_in_metadata(j):
    m=load_metadata(); u=False
    for r in m:
        if r['job_id']==j: r['status']='deleted'; u=True; break
    if u: save_metadata(m)
    return u
def mark_file_failed_cleanup_in_metadata(j):
    m=load_metadata(); u=False
    for r in m:
        if r['job_id']==j: r['status']='failed_cleanup'; u=True; break
    if u: save_metadata(m)
    return u
