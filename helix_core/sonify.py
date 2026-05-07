# sonify.py
# Lightweight helpers to turn DNA/protein sequences into MIDI
# helix_core/sonify.py
from __future__ import annotations
from typing import Iterable, List

# ---- simple sanitizers ----
def dna_only(s: str) -> str:
    return "".join(ch for ch in (s or "").upper() if ch in "ACGT")

def aa_only(s: str) -> str:
    return "".join(ch for ch in (s or "").upper() if ch in "ACDEFGHIKLMNPQRSTVWY")

# ---- mappings -> MIDI note numbers (no colors/styles, just pitches) ----
# Map nucleotides to a pentatonic-ish scale degrees around base_note
_DNA_STEPS = {"A": 0, "C": 2, "G": 4, "T": 7}

# Spread 20 amino acids across ~two octaves deterministically
_AA_ORDER = list("ACDEFGHIKLMNPQRSTVWY")
def _aa_step(a: str) -> int:
    idx = _AA_ORDER.index(a) if a in _AA_ORDER else 0
    return idx  # 0..19 semitone offsets

def dna_to_pitches(dna: str, *, base_note: int = 60) -> List[int]:
    dna = dna_only(dna)
    return [base_note + _DNA_STEPS[n] for n in dna]

def aa_to_pitches(aa: str, *, base_note: int = 60) -> List[int]:
    aa = aa_only(aa)
    return [base_note + _aa_step(a) for a in aa]

# ---- tiny MIDI writer (format 0, single track), no external deps ----
def _vlq(n: int) -> bytes:
    """variable-length quantity encoding"""
    bytes_rev = [n & 0x7F]
    n >>= 7
    while n:
        bytes_rev.append(0x80 | (n & 0x7F))
        n >>= 7
    return bytes(bytearray(reversed(bytes_rev)))

def _meta(delta: int, typ: int, data: bytes) -> bytes:
    return _vlq(delta) + b"\xff" + bytes([typ]) + _vlq(len(data)) + data

def _tempo_meta(bpm: float) -> bytes:
    # microseconds per quarter note
    us_per_qn = int(60_000_000 / max(1e-6, float(bpm)))
    return _meta(0, 0x51, us_per_qn.to_bytes(3, "big"))

def _program_change(delta: int, channel: int, program: int) -> bytes:
    return _vlq(delta) + bytes([0xC0 | (channel & 0x0F), program & 0x7F])

def _note_on(delta: int, ch: int, note: int, vel: int) -> bytes:
    return _vlq(delta) + bytes([0x90 | (ch & 0x0F), note & 0x7F, vel & 0x7F])

def _note_off(delta: int, ch: int, note: int, vel: int) -> bytes:
    return _vlq(delta) + bytes([0x80 | (ch & 0x0F), note & 0x7F, vel & 0x7F])

def make_midi(
    pitches: Iterable[int],
    *,
    bpm: float = 120.0,
    program: int = 0,          # 0..127 GM program (0=Acoustic Grand)
    note_len_beats: float = 0.5,
    velocity: int = 96,
    ticks_per_quarter: int = 480,
) -> bytes:
    """
    Return a Standard MIDI File (SMF) bytes (format 0, single track).
    Each pitch becomes a note with fixed length 'note_len_beats'.
    """
    notes = [max(0, min(127, int(p))) for p in pitches]
    tpq = int(ticks_per_quarter)
    note_ticks = max(1, int(round(note_len_beats * tpq)))

    # Track data
    track = bytearray()
    track += _tempo_meta(bpm)
    track += _program_change(0, 0, int(program) & 0x7F)

    first = True
    for n in notes:
        # space notes back-to-back: delta 0 for first note_on, else 0 because previous note_off already consumed time
        track += _note_on(0 if first else 0, 0, n, velocity)
        track += _note_off(note_ticks, 0, n, 64)
        first = False

    # End of track
    track += _meta(0, 0x2F, b"")

    # Track chunk
    trk_chunk = b"MTrk" + len(track).to_bytes(4, "big") + bytes(track)

    # Header chunk (format 0, one track)
    hdr = bytearray()
    hdr += b"MThd" + (6).to_bytes(4, "big")
    hdr += (0).to_bytes(2, "big")   # format 0
    hdr += (1).to_bytes(2, "big")   # ntrks
    hdr += tpq.to_bytes(2, "big")   # division
    return bytes(hdr) + trk_chunk

import io

try:
    import mido
except ImportError:  # app can still run; UI will show an install hint
    mido = None


def aa_only(seq: str) -> str:
    return "".join(ch for ch in (seq or "").upper() if ch in "ACDEFGHIKLMNPQRSTVWY")


def dna_only(seq: str) -> str:
    return "".join(ch for ch in (seq or "").upper() if ch in "ACGTU").replace("U", "T")


def aa_to_pitches(seq: str, base_note: int = 60) -> list[int]:
    """Map 20 AAs to notes within one octave (base_note=60 -> C4)."""
    order = "ARNDCQEGHILKMFPSTWYV"
    return [base_note + (order.index(a) % 12) for a in aa_only(seq)]


def dna_to_pitches(seq: str, base_note: int = 60) -> list[int]:
    """Simple DNA mapping: A=C, C=D, G=E, T=F."""
    m = {"A": 0, "C": 2, "G": 4, "T": 5}
    return [base_note + m[b] for b in dna_only(seq)]


def make_midi(
    pitches: list[int],
    bpm: int = 120,
    program: int = 0,
    note_len_beats: float = 0.5,
    ticks_per_beat: int = 480,
) -> bytes:
    """Build a single-track MIDI from MIDI note numbers."""
    if mido is None:
        raise RuntimeError("Missing dependency: mido. Install with: pip install mido")

    mid = mido.MidiFile(ticks_per_beat=ticks_per_beat)
    track = mido.MidiTrack()
    mid.tracks.append(track)

    track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(int(bpm))))
    track.append(mido.Message("program_change", program=int(program), time=0))

    dur = max(1, int(note_len_beats * ticks_per_beat))
    for p in pitches:
        track.append(mido.Message("note_on", note=int(p), velocity=80, time=0))
        track.append(mido.Message("note_off", note=int(p), velocity=0, time=dur))

    buf = io.BytesIO()
    mid.save(file=buf)
    return buf.getvalue()


