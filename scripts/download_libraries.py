"""
Download or synthesize Brunello / GeCKO CRISPR libraries and import into helix.db.
Usage (from repo root):  python scripts/download_libraries.py
"""
from __future__ import annotations

import csv
import io
import random
import sqlite3
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from helix_core.scoring_model import score_guide_ml

_DB_PATH = Path("helix.db")

_BRUNELLO_URL = (
    "https://www.addgene.org/static/cms/filer_public/8b/4c/"
    "8b4c89d9-eac1-44b2-af1f-d3efa4a0c0e2/broadgpp-brunello-library-contents.txt"
)
_GECKO_URL = (
    "https://www.addgene.org/static/cms/filer_public/80/d5/"
    "80d547e1-00bb-40c8-8004-f87a5da8c11a/humageckov2.csv"
)

_BASES = "ACGT"

_SYNTHETIC_GENES_50 = [
    "TP53", "BRCA1", "BRCA2", "KRAS", "MYC", "PTEN", "APC", "RB1", "VHL",
    "EGFR", "BRAF", "PIK3CA", "IDH1", "IDH2", "NOTCH1", "CDKN2A", "CDH1",
    "SMAD4", "CTNNB1", "ARID1A", "DNMT3A", "FLT3", "NPM1", "RUNX1",
    "JAK2", "BCR", "ABL1", "PML", "RARA", "MLH1", "MSH2", "MSH6",
    "ATM", "CHEK2", "PALB2", "RAD51", "FANCA", "FANCD2", "FANCF",
    "PDCD1", "CD274", "CTLA4", "LAG3", "TIM3", "TIGIT", "HAVCR2",
    "DNMT1", "TET2", "ASXL1", "EZH2",
]

_EXTRA_GENES_50 = [
    "STAT3", "STAT5A", "IRF3", "IRF7", "MYD88", "TBK1", "IKBKE",
    "NFKB1", "RELA", "RELB", "BCL2", "BCL2L1", "BAX", "BAK1",
    "CASP3", "CASP8", "CASP9", "FADD", "TRADD", "TRAF2", "TRAF6",
    "MAP3K7", "MAP2K4", "MAPK8", "MAPK14", "RAF1", "MAP2K1", "MAPK3",
    "MTOR", "RPTOR", "AKT1", "AKT2", "PDK1", "INSR", "IGF1R",
    "GRB2", "SOS1", "HRAS", "NRAS", "RAC1", "CDC42", "RHOA",
    "SRC", "YES1", "FYN", "LCK", "ZAP70", "BTK", "SYK", "JAK1",
]


def _random_guide() -> str:
    return "".join(random.choice(_BASES) for _ in range(20))


# ─── schema ───────────────────────────────────────────────────────────────────

def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS grna_library (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            gene           TEXT    NOT NULL,
            guide_sequence TEXT    NOT NULL,
            pam            TEXT    DEFAULT 'NGG',
            library        TEXT    NOT NULL,
            score          REAL    DEFAULT 0.0,
            created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS grna_library_fts USING fts5(
            gene, guide_sequence, library
        );
    """)
    conn.commit()


# ─── bulk insert helpers ──────────────────────────────────────────────────────

def _insert_guides(conn: sqlite3.Connection, rows: list[tuple]) -> int:
    """rows: [(gene, guide_seq, library), ...]. Validates and scores each guide."""
    inserted = 0
    for gene, guide_seq, library in rows:
        guide_seq = guide_seq.upper().strip()
        if len(guide_seq) != 20 or any(b not in _BASES for b in guide_seq):
            continue
        gene = gene.upper().strip()
        if not gene:
            continue
        score = score_guide_ml(guide_seq)
        conn.execute(
            "INSERT INTO grna_library (gene, guide_sequence, library, score) VALUES (?, ?, ?, ?)",
            (gene, guide_seq, library, score),
        )
        inserted += 1
    conn.commit()
    return inserted


def _rebuild_fts(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM grna_library_fts")
    conn.execute(
        "INSERT INTO grna_library_fts(rowid, gene, guide_sequence, library) "
        "SELECT id, gene, guide_sequence, library FROM grna_library"
    )
    conn.commit()


# ─── Brunello ─────────────────────────────────────────────────────────────────

def _parse_brunello_tsv(text: str) -> list[tuple]:
    rows = []
    reader = csv.reader(io.StringIO(text), delimiter="\t")
    for line in reader:
        if not line or line[0].startswith("#"):
            continue
        if len(line) < 3:
            continue
        # Columns: Gene ID, Gene Symbol, sgRNA Sequence
        gene  = line[1].strip()
        guide = line[2].strip().upper()
        if gene and guide and gene not in ("Gene Symbol", "Target Gene Symbol", ""):
            rows.append((gene, guide, "brunello"))
    return rows


def _download_brunello(conn: sqlite3.Connection) -> int:
    print("  Downloading Brunello library from Addgene…")
    try:
        req = urllib.request.Request(_BRUNELLO_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            text = r.read().decode("utf-8", errors="ignore")
        rows = _parse_brunello_tsv(text)
        if not rows:
            raise ValueError("Parsed 0 rows")
        print(f"  Parsed {len(rows):,} rows from Brunello file")
        return _insert_guides(conn, rows)
    except Exception as exc:
        print(f"  Brunello download failed: {exc}")
        return 0


def _synthetic_brunello(conn: sqlite3.Connection) -> int:
    print("  Generating synthetic Brunello data (50 genes × 5 guides)…")
    rows = [(gene, _random_guide(), "brunello")
            for gene in _SYNTHETIC_GENES_50
            for _ in range(5)]
    return _insert_guides(conn, rows)


# ─── GeCKO ────────────────────────────────────────────────────────────────────

def _parse_gecko_csv(text: str) -> list[tuple]:
    rows = []
    reader = csv.DictReader(io.StringIO(text))
    header = [h.lower().strip() for h in (reader.fieldnames or [])]

    def _pick(row, *keys):
        for k in keys:
            for h in header:
                if k in h:
                    return row.get(h, "").strip()
        return ""

    for row in reader:
        gene  = _pick(row, "gene symbol", "target gene", "gene").upper()
        guide = _pick(row, "sgrna target", "sequence", "guide").upper()
        if gene and guide:
            rows.append((gene, guide, "gecko"))
    return rows


def _download_gecko(conn: sqlite3.Connection) -> int:
    print("  Downloading GeCKO v2 library from Addgene…")
    try:
        req = urllib.request.Request(_GECKO_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            text = r.read().decode("utf-8", errors="ignore")
        rows = _parse_gecko_csv(text)
        if not rows:
            raise ValueError("Parsed 0 rows")
        print(f"  Parsed {len(rows):,} rows from GeCKO file")
        return _insert_guides(conn, rows)
    except Exception as exc:
        print(f"  GeCKO download failed: {exc}")
        return 0


def _synthetic_gecko(conn: sqlite3.Connection) -> int:
    all_genes = (_SYNTHETIC_GENES_50 + _EXTRA_GENES_50)[:100]
    print(f"  Generating synthetic GeCKO data ({len(all_genes)} genes × 5 guides)…")
    rows = [(gene, _random_guide(), "gecko")
            for gene in all_genes
            for _ in range(5)]
    return _insert_guides(conn, rows)


# ─── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"Database: {_DB_PATH.resolve()}\n")
    conn = sqlite3.connect(str(_DB_PATH))

    _init_schema(conn)
    conn.execute("DELETE FROM grna_library")
    conn.execute("DELETE FROM grna_library_fts")
    conn.commit()

    print("[1/2] Brunello library")
    n = _download_brunello(conn)
    if n == 0:
        n = _synthetic_brunello(conn)
    print(f"      → {n:,} Brunello guides imported")

    print("\n[2/2] GeCKO v2 library")
    n = _download_gecko(conn)
    if n == 0:
        n = _synthetic_gecko(conn)
    print(f"      → {n:,} GeCKO guides imported")

    print("\nRebuilding FTS index…")
    _rebuild_fts(conn)

    total = conn.execute("SELECT COUNT(*) FROM grna_library").fetchone()[0]
    genes = conn.execute("SELECT COUNT(DISTINCT gene) FROM grna_library").fetchone()[0]
    conn.close()

    print(f"\nDone. {total:,} guides imported, {genes:,} genes covered.")


if __name__ == "__main__":
    main()
