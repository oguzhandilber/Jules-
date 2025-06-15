import os; from flask import current_app
def send_email(r, s, bh, bt=None):
    l = current_app.logger if current_app else None
    msg = f"SIMULATED EMAIL To: {r}\nSubject: {s}\nBody: {bh}"
    if l: l.info(msg)
    else: print(msg)
    return True
