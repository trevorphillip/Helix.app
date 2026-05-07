from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from io import StringIO

from fastapi import APIRouter, HTTPException, Query

from api.db import get_conn, init_tables

try:
    from Bio import Entrez, SeqIO
    Entrez.email = "helix@app.com"
    _BIO_OK = True
except ImportError:
    _BIO_OK = False

router = APIRouter()
init_tables()

_CACHE_DAYS = 7

_ORGANISM_MAP = {
    "human":  "Homo sapiens",
    "mouse":  "Mus musculus",
    "ecoli":  "Escherichia coli",
    "e. coli": "Escherichia coli",
    "yeast":  "Saccharomyces cerevisiae",
    "all":    "",
}

# ─── hardcoded common genes ───────────────────────────────────────────────────

_COMMON_GENES = [
    # ── Tumor suppressors ──
    {"name":"TP53",   "description":"Tumor protein p53, master regulator of cell cycle arrest and apoptosis",
     "accession":"NM_000546", "organism":"Homo sapiens", "category":"tumor_suppressor"},
    {"name":"BRCA1",  "description":"Breast cancer type 1 susceptibility protein, DNA damage repair",
     "accession":"NM_007294", "organism":"Homo sapiens", "category":"tumor_suppressor"},
    {"name":"BRCA2",  "description":"Breast cancer type 2 susceptibility protein, homologous recombination",
     "accession":"NM_000059", "organism":"Homo sapiens", "category":"tumor_suppressor"},
    {"name":"RB1",    "description":"Retinoblastoma protein, cell cycle entry checkpoint",
     "accession":"NM_000321", "organism":"Homo sapiens", "category":"tumor_suppressor"},
    {"name":"PTEN",   "description":"Phosphatase and tensin homolog, PI3K/AKT pathway inhibitor",
     "accession":"NM_000314", "organism":"Homo sapiens", "category":"tumor_suppressor"},
    {"name":"APC",    "description":"Adenomatous polyposis coli, Wnt signaling negative regulator",
     "accession":"NM_000038", "organism":"Homo sapiens", "category":"tumor_suppressor"},
    {"name":"VHL",    "description":"Von Hippel-Lindau tumour suppressor, HIF-1α degradation",
     "accession":"NM_000551", "organism":"Homo sapiens", "category":"tumor_suppressor"},
    {"name":"STK11",  "description":"Serine threonine kinase 11 (LKB1), AMPK activator",
     "accession":"NM_000455", "organism":"Homo sapiens", "category":"tumor_suppressor"},
    {"name":"MLH1",   "description":"MutL homolog 1, DNA mismatch repair",
     "accession":"NM_000249", "organism":"Homo sapiens", "category":"tumor_suppressor"},
    {"name":"MSH2",   "description":"MutS homolog 2, DNA mismatch repair",
     "accession":"NM_000251", "organism":"Homo sapiens", "category":"tumor_suppressor"},
    # ── Oncogenes ──
    {"name":"KRAS",   "description":"KRAS proto-oncogene GTPase, most frequently mutated in cancer",
     "accession":"NM_004985", "organism":"Homo sapiens", "category":"oncogene"},
    {"name":"MYC",    "description":"MYC proto-oncogene, bHLH transcription factor",
     "accession":"NM_002467", "organism":"Homo sapiens", "category":"oncogene"},
    {"name":"EGFR",   "description":"Epidermal growth factor receptor, receptor tyrosine kinase",
     "accession":"NM_005228", "organism":"Homo sapiens", "category":"oncogene"},
    {"name":"BRAF",   "description":"B-Raf proto-oncogene, serine/threonine kinase",
     "accession":"NM_004333", "organism":"Homo sapiens", "category":"oncogene"},
    {"name":"PIK3CA", "description":"PI3-kinase catalytic subunit alpha, lipid kinase",
     "accession":"NM_006218", "organism":"Homo sapiens", "category":"oncogene"},
    {"name":"ALK",    "description":"Anaplastic lymphoma kinase, receptor tyrosine kinase",
     "accession":"NM_004304", "organism":"Homo sapiens", "category":"oncogene"},
    {"name":"RET",    "description":"RET proto-oncogene, glial cell-line derived neurotrophic factor receptor",
     "accession":"NM_020975", "organism":"Homo sapiens", "category":"oncogene"},
    {"name":"MET",    "description":"MET proto-oncogene, hepatocyte growth factor receptor",
     "accession":"NM_000245", "organism":"Homo sapiens", "category":"oncogene"},
    {"name":"MDM2",   "description":"MDM2 proto-oncogene, p53 E3 ubiquitin ligase",
     "accession":"NM_002392", "organism":"Homo sapiens", "category":"oncogene"},
    {"name":"CDK4",   "description":"Cyclin dependent kinase 4, G1/S cell cycle transition",
     "accession":"NM_000075", "organism":"Homo sapiens", "category":"oncogene"},
    # ── Immune checkpoints ──
    {"name":"PDCD1",  "description":"Programmed cell death protein 1 (PD-1), T cell inhibitory receptor",
     "accession":"NM_005018", "organism":"Homo sapiens", "category":"immune_checkpoint"},
    {"name":"CD274",  "description":"Programmed death ligand 1 (PD-L1), immune checkpoint ligand",
     "accession":"NM_014143", "organism":"Homo sapiens", "category":"immune_checkpoint"},
    {"name":"CTLA4",  "description":"Cytotoxic T-lymphocyte-associated protein 4, T cell co-inhibitory",
     "accession":"NM_005214", "organism":"Homo sapiens", "category":"immune_checkpoint"},
    {"name":"LAG3",   "description":"Lymphocyte activation gene 3, MHC class II binding inhibitory receptor",
     "accession":"NM_002286", "organism":"Homo sapiens", "category":"immune_checkpoint"},
    {"name":"TIGIT",  "description":"T cell immunoreceptor with Ig and ITIM domains",
     "accession":"NM_173799", "organism":"Homo sapiens", "category":"immune_checkpoint"},
    {"name":"HAVCR2", "description":"TIM-3, hepatitis A virus cellular receptor 2, exhaustion marker",
     "accession":"NM_032782", "organism":"Homo sapiens", "category":"immune_checkpoint"},
    {"name":"VSIR",   "description":"VISTA/PD-1H, V-type immunoglobulin domain T cell suppressor",
     "accession":"NM_022153", "organism":"Homo sapiens", "category":"immune_checkpoint"},
    {"name":"CD276",  "description":"B7-H3, immune checkpoint co-inhibitory ligand",
     "accession":"NM_001024736", "organism":"Homo sapiens", "category":"immune_checkpoint"},
    {"name":"SIRPA",  "description":"Signal regulatory protein alpha, CD47 'don't eat me' receptor",
     "accession":"NM_080792", "organism":"Homo sapiens", "category":"immune_checkpoint"},
    {"name":"KLRB1",  "description":"CD161/NKR-P1, NK cell lectin-like receptor",
     "accession":"NM_002258", "organism":"Homo sapiens", "category":"immune_checkpoint"},
    # ── Housekeeping ──
    {"name":"ACTB",   "description":"Actin beta, cytoskeletal structural protein",
     "accession":"NM_001101", "organism":"Homo sapiens", "category":"housekeeping"},
    {"name":"GAPDH",  "description":"Glyceraldehyde-3-phosphate dehydrogenase, glycolytic enzyme",
     "accession":"NM_002046", "organism":"Homo sapiens", "category":"housekeeping"},
    {"name":"HPRT1",  "description":"Hypoxanthine phosphoribosyltransferase 1, purine synthesis",
     "accession":"NM_000194", "organism":"Homo sapiens", "category":"housekeeping"},
    {"name":"B2M",    "description":"Beta-2-microglobulin, MHC class I light chain",
     "accession":"NM_004048", "organism":"Homo sapiens", "category":"housekeeping"},
    {"name":"TUBB",   "description":"Tubulin beta class I, microtubule component",
     "accession":"NM_178014", "organism":"Homo sapiens", "category":"housekeeping"},
    {"name":"LDHA",   "description":"Lactate dehydrogenase A, anaerobic glycolysis",
     "accession":"NM_005566", "organism":"Homo sapiens", "category":"housekeeping"},
    {"name":"ENO1",   "description":"Enolase 1, glycolytic enzyme and moonlighting protein",
     "accession":"NM_001428", "organism":"Homo sapiens", "category":"housekeeping"},
    {"name":"PGK1",   "description":"Phosphoglycerate kinase 1, ATP-generating glycolytic step",
     "accession":"NM_000291", "organism":"Homo sapiens", "category":"housekeeping"},
    {"name":"HSPA1A", "description":"Heat shock protein 70 (HSP70), stress chaperone",
     "accession":"NM_005345", "organism":"Homo sapiens", "category":"housekeeping"},
    {"name":"HNRNPA1","description":"Heterogeneous nuclear ribonucleoprotein A1, RNA processing",
     "accession":"NM_002136", "organism":"Homo sapiens", "category":"housekeeping"},
    # ── CRISPR essential ──
    {"name":"PCNA",   "description":"Proliferating cell nuclear antigen, DNA polymerase processivity clamp",
     "accession":"NM_182649", "organism":"Homo sapiens", "category":"crispr_essential"},
    {"name":"RPA1",   "description":"Replication protein A 70 kDa subunit, ssDNA binding",
     "accession":"NM_002945", "organism":"Homo sapiens", "category":"crispr_essential"},
    {"name":"RAD51",  "description":"RAD51 recombinase, homologous recombination strand exchange",
     "accession":"NM_133487", "organism":"Homo sapiens", "category":"crispr_essential"},
    {"name":"XRCC1",  "description":"X-ray repair cross complementing 1, base excision repair scaffold",
     "accession":"NM_006297", "organism":"Homo sapiens", "category":"crispr_essential"},
    {"name":"LIG4",   "description":"DNA ligase 4, non-homologous end joining final step",
     "accession":"NM_002312", "organism":"Homo sapiens", "category":"crispr_essential"},
    {"name":"POLR2A", "description":"RNA polymerase II largest subunit, mRNA transcription",
     "accession":"NM_000937", "organism":"Homo sapiens", "category":"crispr_essential"},
    {"name":"SF3B1",  "description":"Splicing factor 3b subunit 1, U2 snRNP branch-point binding",
     "accession":"NM_012433", "organism":"Homo sapiens", "category":"crispr_essential"},
    {"name":"SRSF1",  "description":"Serine arginine rich splicing factor 1, exonic splicing enhancer",
     "accession":"NM_006924", "organism":"Homo sapiens", "category":"crispr_essential"},
    {"name":"HNRNPC", "description":"Heterogeneous nuclear ribonucleoprotein C, pre-mRNA binding",
     "accession":"NM_004500", "organism":"Homo sapiens", "category":"crispr_essential"},
    {"name":"POP1",   "description":"POP1 homolog, largest subunit of RNase P/MRP complexes",
     "accession":"NM_015029", "organism":"Homo sapiens", "category":"crispr_essential"},
]


# ─── cache helpers ────────────────────────────────────────────────────────────

def _cache_get_search(query: str, organism: str) -> list[dict] | None:
    conn = get_conn()
    cutoff = (datetime.utcnow() - timedelta(days=_CACHE_DAYS)).isoformat()
    row = conn.execute(
        "SELECT results_json FROM gene_cache WHERE query=? AND organism=? AND fetched_at > ? LIMIT 1",
        (query.lower(), organism.lower(), cutoff),
    ).fetchone()
    conn.close()
    return json.loads(row["results_json"]) if row else None


def _cache_put_search(query: str, organism: str, results: list[dict]) -> None:
    conn = get_conn()
    conn.execute(
        "INSERT INTO gene_cache (query, organism, results_json) VALUES (?,?,?)",
        (query.lower(), organism.lower(), json.dumps(results)),
    )
    conn.commit()
    conn.close()


def _cache_get_seq(accession: str) -> dict | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT accession, name, organism, sequence, length FROM sequence_cache WHERE accession=?",
        (accession.upper(),),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def _cache_put_seq(data: dict) -> None:
    conn = get_conn()
    conn.execute(
        """INSERT OR REPLACE INTO sequence_cache (accession, name, organism, sequence, length)
           VALUES (?,?,?,?,?)""",
        (data["accession"].upper(), data.get("name",""), data.get("organism",""),
         data["sequence"], data["length"]),
    )
    conn.commit()
    conn.close()


# ─── NCBI helpers ─────────────────────────────────────────────────────────────

def _ncbi_search(query: str, organism: str) -> list[dict]:
    if not _BIO_OK:
        raise RuntimeError("biopython not installed")

    org_sci = _ORGANISM_MAP.get(organism.lower(), "Homo sapiens")
    term = f"{query}[Gene Name]" + (f" AND {org_sci}[Organism]" if org_sci else "")

    handle = Entrez.esearch(db="gene", term=term, retmax=10)
    search_rec = Entrez.read(handle)
    handle.close()

    ids = search_rec.get("IdList", [])
    if not ids:
        return []

    handle = Entrez.esummary(db="gene", id=",".join(ids), retmode="xml")
    summaries = Entrez.read(handle)
    handle.close()

    results: list[dict] = []
    doc_list = summaries.get("DocumentSummarySet", {}).get("DocumentSummary", [])
    for doc in doc_list:
        try:
            gene_id = doc.attributes.get("uid", "") if hasattr(doc, "attributes") else str(doc.get("Id",""))
            name = str(doc.get("NomenclatureSymbol") or doc.get("Name") or "")
            description = str(doc.get("Description") or "")
            org_obj = doc.get("Organism", {})
            organism_name = str(org_obj.get("ScientificName","") if isinstance(org_obj, dict) else "")
            results.append({
                "gene_id": gene_id,
                "name": name,
                "description": description,
                "organism": organism_name,
                "accession": gene_id,
            })
        except Exception:
            continue
    return results


def _ncbi_fetch_sequence(accession: str) -> dict:
    if not _BIO_OK:
        raise RuntimeError("biopython not installed")

    fetch_id = accession

    # If it's a plain Gene ID, resolve to an NM_ accession first
    if accession.isdigit():
        handle = Entrez.elink(dbfrom="gene", db="nuccore", id=accession, linkname="gene_nuccore_refseqrna")
        link_records = Entrez.read(handle)
        handle.close()

        nuccore_id = None
        for rec in link_records:
            for db_to in rec.get("LinkSetDb", []):
                links = db_to.get("Link", [])
                if links:
                    nuccore_id = links[0]["Id"]
                    break
            if nuccore_id:
                break

        if not nuccore_id:
            raise ValueError(f"No linked RefSeq mRNA for Gene ID {accession}")

        handle = Entrez.efetch(db="nuccore", id=nuccore_id, rettype="acc", retmode="text")
        fetch_id = handle.read().strip()
        handle.close()

    handle = Entrez.efetch(db="nucleotide", id=fetch_id, rettype="gb", retmode="text")
    record = SeqIO.read(StringIO(handle.read()), "genbank")
    handle.close()

    seq_str  = str(record.seq)
    name     = record.description or fetch_id
    organism = record.annotations.get("organism", "")
    base_acc = fetch_id.split(".")[0]

    return {
        "accession": base_acc,
        "name":      name,
        "organism":  organism,
        "sequence":  seq_str,
        "length":    len(seq_str),
    }


# ─── routes ───────────────────────────────────────────────────────────────────

@router.get("/genes/common")
def get_common_genes() -> list[dict]:
    return _COMMON_GENES


@router.get("/genes/search")
def search_genes(
    query: str = Query(..., min_length=1),
    organism: str = Query(default="human"),
) -> dict:
    cached = _cache_get_search(query, organism)
    if cached is not None:
        return {"results": cached, "cached": True}

    if not _BIO_OK:
        raise HTTPException(status_code=503, detail="biopython not available")

    try:
        results = _ncbi_search(query, organism)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"NCBI search failed: {exc}") from exc

    _cache_put_search(query, organism, results)
    return {"results": results, "cached": False}


@router.get("/genes/fetch/{accession}")
def fetch_gene_sequence(accession: str) -> dict:
    cached = _cache_get_seq(accession)
    if cached:
        return cached

    if not _BIO_OK:
        raise HTTPException(status_code=503, detail="biopython not available")

    try:
        data = _ncbi_fetch_sequence(accession)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"NCBI fetch failed: {exc}") from exc

    _cache_put_seq(data)
    return data
