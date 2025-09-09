# io_utils.py
from typing import Tuple, Dict, Any, Optional
from Bio import SeqIO
from io import StringIO

def load_sequence_file(file_bytes, filename: str) -> Tuple[str, Dict[str, Any]]:
    """
    Read FASTA (.fa/.fasta) or GenBank (.gb/.gbk) into (sequence, metadata).
    """
    name = filename or "input"
    fn = filename.lower()
    data = file_bytes.read().decode("utf-8", errors="ignore")

    if fn.endswith((".fa", ".fasta")):
        handle = StringIO(data)
        recs = list(SeqIO.parse(handle, "fasta"))
        if not recs:
            return "", {"name": name}
        seq = str(recs[0].seq).upper()
        meta = {"name": recs[0].id or name, "description": recs[0].description}
        return seq, meta

    if fn.endswith((".gb", ".gbk")):
        handle = StringIO(data)
        recs = list(SeqIO.parse(handle, "genbank"))
        if not recs:
            return "", {"name": name}
        seq = str(recs[0].seq).upper()
        feats = [{"type": f.type, "start": int(f.location.start), "end": int(f.location.end)}
                 for f in recs[0].features]
        meta = {"name": recs[0].id or name, "description": recs[0].description, "features": feats}
        return seq, meta

    # fallback: try FASTA parsing
    handle = StringIO(data)
    recs = list(SeqIO.parse(handle, "fasta"))
    if recs:
        return str(recs[0].seq).upper(), {"name": recs[0].id or name, "description": recs[0].description}
    return data.strip().upper(), {"name": name}

def to_fasta(name: str, sequence: str, width: int = 70) -> str:
    lines = [f">{name}"]
    for i in range(0, len(sequence), width):
        lines.append(sequence[i:i+width])
    return "\n".join(lines)

def save_text_download(label: str, content: str, filename: str, st):
    st.download_button(
        label, data=content.encode("utf-8"),
        file_name=filename, mime="text/plain",
        use_container_width=True
    )
def load_multifasta_file(file_bytes) -> str:
    return file_bytes.read().decode("utf-8", errors="ignore")
