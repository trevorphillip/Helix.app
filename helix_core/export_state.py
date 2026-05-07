# export_state.py
import json

STATE_KEYS = [
    "sequence", "win", "tut_seq_pep", "tut_segs", "pdb_current",
    # add anything else you want to persist
]

def export_state(ss) -> bytes:
    snap = {}
    for k in STATE_KEYS:
        if k in ss:
            snap[k] = ss[k]
    return json.dumps(snap, indent=2).encode("utf-8")

def import_state(ss, payload: bytes):
    obj = json.loads(payload.decode("utf-8", errors="ignore"))
    for k, v in obj.items():
        ss[k] = v
