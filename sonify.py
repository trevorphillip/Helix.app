# sonify.py
# Lightweight helpers to turn DNA/protein sequences into MIDI

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


