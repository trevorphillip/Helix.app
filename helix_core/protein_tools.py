# protein_tools.py
import io
import numpy as np

# Try Bio.PDB for robust parsing; fall back to simple CA-line parser
try:
    from Bio.PDB import PDBParser
    from Bio.PDB.Polypeptide import is_aa
    _HAS_BIOPDB = True
except Exception:
    _HAS_BIOPDB = False

def ca_coords_from_pdb(pdb_text: str, chains=None):
    """
    Return (X, labels) where X is Nx3 array of Cα coordinates and
    labels is [(chain, resi)] of length N. 'chains' is an optional whitelist.
    """
    chains = set(chains) if chains else None
    if _HAS_BIOPDB:
        parser = PDBParser(QUIET=True)
        struct = parser.get_structure("x", io.StringIO(pdb_text))
        model = next(struct.get_models())
        coords, labels = [], []
        for ch in model.get_chains():
            if chains and ch.id not in chains:
                continue
            for res in ch.get_residues():
                if is_aa(res, standard=True) and "CA" in res:
                    v = res["CA"].get_vector().get_array()
                    coords.append(v)
                    labels.append((ch.id, int(res.id[1])))
        if coords:
            return np.vstack(coords), labels

    # Fallback: parse 'ATOM' CA records
    coords, labels = [], []
    for line in pdb_text.splitlines():
        if not line.startswith("ATOM"):
            continue
        name = line[12:16].strip()
        if name != "CA":
            continue
        chain = line[21].strip() or "A"
        if chains and chain not in chains:
            continue
        try:
            resi = int(line[22:26])
            x = float(line[30:38]); y = float(line[38:46]); z = float(line[46:54])
        except Exception:
            continue
        coords.append([x, y, z]); labels.append((chain, resi))
    if not coords:
        return np.zeros((0,3)), []
    return np.array(coords, dtype=float), labels

def contact_matrix(X: np.ndarray) -> np.ndarray:
    """Pairwise Euclidean distance matrix for Nx3 coordinates."""
    if X.size == 0:
        return np.zeros((0,0))
    d = X[:, None, :] - X[None, :, :]
    return np.sqrt((d * d).sum(axis=2))

def contact_edges(D: np.ndarray, cutoff: float = 8.0):
    """Return list of (i, j, dist) with i<j and dist <= cutoff."""
    n = D.shape[0]
    out = []
    for i in range(n):
        for j in range(i+1, n):
            dij = float(D[i, j])
            if dij <= cutoff:
                out.append((i, j, dij))
    out.sort(key=lambda t: t[2])
    return out
