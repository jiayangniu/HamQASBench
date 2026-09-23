"""Benchmark artifact metadata: benchmark instance manifest + checksums.

Generates, for the 13 benchmark molecules registered in bench_utils:
  artifact/instances.csv     one row per benchmark instance with full metadata
  artifact/instances.json    same content, machine-readable
  artifact/mol_data.sha256   SHA-256 checksums of every benchmark .npz file

Metadata per instance: tier, n_qubits, active space (from npz metadata when
stored, else from the documented CAS table in mol_gen/prepare_molecules.py),
basis, charge, mapping, geometry (parsed from the canonical filename),
E0 (electronic + total), spectral gap, ground-state degeneracy, Pauli-term
count, and file checksum.

Only small npz members (eigvals, weights, metadata scalars) are read — the
dense Hamiltonian matrices are never loaded.

Run:
    conda run -n psqasbench python artifact/gen_manifest.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bench_utils import FINAL_SUITE_MOL_FILES, MOL_DIR   # noqa: E402

OUT_DIR = Path(__file__).resolve().parent
DEGEN_TOL = 1e-6

# CAS definitions documented in mol_gen/prepare_molecules.py and
# mol_gen/prepare_beh2_basis_series.py. npz metadata overrides when present.
DOCUMENTED_CAS = {
    "T1_BeH2_STO3G_6q":     dict(active_electrons=2, active_orbitals=3, basis="sto-3g",  charge=0),
    "T1_LiH_Equil_6q":      dict(active_electrons=2, active_orbitals=3, basis="sto-3g",  charge=0),
    "T2_CH2_8q":            dict(active_electrons=2, active_orbitals=4, basis="sto-3g",  charge=0),
    "T3_H2_Stretch_4q":     dict(active_electrons=2, active_orbitals=2, basis="sto-3g",  charge=0),
    "T3_H2O_StrongCorr_8q": dict(active_electrons=4, active_orbitals=4, basis="sto-3g",  charge=0),
    "T3_H4_Chain_8q":       dict(active_electrons=4, active_orbitals=4, basis="sto-3g",  charge=0),
    "T4_H3_Linear_6q":      dict(active_electrons=2, active_orbitals=3, basis="sto-3g",  charge=1),
    "T5_BeH2_631G_8q":      dict(active_electrons=2, active_orbitals=4, basis="6-31g",   charge=0),
    "T5_BeH2_6311G_10q":    dict(active_electrons=2, active_orbitals=5, basis="6-311g",  charge=0),
    "T5_BeH2_CCPVDZ_12q":   dict(active_electrons=2, active_orbitals=6, basis="cc-pvdz", charge=0),
    "T5_BeH2_CCPVDZ_14q":   dict(active_electrons=4, active_orbitals=7, basis="cc-pvdz", charge=0),
    # Legacy large-molecule additions (pre-final-suite experiments)
    "H2O_10q":              dict(charge=0),
    "LiH_12q":              dict(charge=0),
}

LEGACY_KEYS = {"H2O_10q", "LiH_12q"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_geometry(filename: str) -> tuple[str, str]:
    """Extract geometry string and mapping from the canonical npz filename."""
    m = re.search(r"geom_(.+)_(jordan_wigner|parity)\.npz$", filename)
    if not m:
        return "", ""
    return m.group(1).replace("_", " "), m.group(2)


def instance_metadata(mol_key: str, filename: str) -> dict | None:
    path = MOL_DIR / filename
    if not path.exists():
        print(f"  [MISSING] {mol_key}: {filename}")
        return None

    print(f"  {mol_key} ...", flush=True)
    data = np.load(path, allow_pickle=True)

    eigvals = np.asarray(data["eigvals"], dtype=float)
    shift = float(data.get("energy_shift", 0.0))
    weights = np.asarray(data["weights"])
    n_qubits_file = int(data["n_qubits"]) if "n_qubits" in data else None

    m = re.search(r"(\d+)q", mol_key)
    n_qubits = n_qubits_file if n_qubits_file else (int(m.group(1)) if m else None)

    e0_el = float(eigvals[0])
    gap01 = float(eigvals[1] - eigvals[0]) if len(eigvals) > 1 else float("nan")
    n_degen = int(np.sum(np.abs(eigvals - eigvals[0]) < DEGEN_TOL))

    doc = dict(DOCUMENTED_CAS.get(mol_key, {}))
    ae = int(data["active_electrons"]) if "active_electrons" in data else doc.get("active_electrons")
    ao = int(data["active_orbitals"])  if "active_orbitals"  in data else doc.get("active_orbitals")
    basis = str(data["basis"]) if "basis" in data else doc.get("basis")
    charge = doc.get("charge")

    geometry, mapping = parse_geometry(filename)
    tier = mol_key.split("_")[0] if mol_key.startswith("T") else "legacy"

    return dict(
        mol_key=mol_key,
        tier=tier,
        legacy=int(mol_key in LEGACY_KEYS),
        n_qubits=n_qubits,
        active_electrons=ae,
        active_orbitals=ao,
        basis=basis,
        charge=charge,
        mapping=mapping,
        geometry_angstrom=geometry,
        n_pauli_terms=int(len(weights)),
        e0_electronic_ha=e0_el,
        energy_shift_ha=shift,
        e0_total_ha=e0_el + shift,
        gap01_ha=gap01,
        gs_degeneracy=n_degen,
        n_eigvals_stored=int(len(eigvals)),
        filename=filename,
        sha256=sha256_file(path),
        size_bytes=path.stat().st_size,
    )


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    print("=== Benchmark instance manifest ===\n")

    rows = []
    for mol_key, filename in FINAL_SUITE_MOL_FILES.items():
        row = instance_metadata(mol_key, filename)
        if row is not None:
            rows.append(row)

    # Validate before opening any reference file for writing.
    if not rows:
        raise SystemExit("No Hamiltonians found; reference manifests were not changed.")

    # instances.csv
    p_csv = OUT_DIR / "instances.csv"
    with p_csv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\n  -> {p_csv} ({len(rows)} instances)")

    # instances.json
    p_json = OUT_DIR / "instances.json"
    p_json.write_text(json.dumps(rows, indent=2))
    print(f"  -> {p_json}")

    # mol_data.sha256 (benchmark files only, canonical sha256sum format)
    p_sha = OUT_DIR / "mol_data.sha256"
    with p_sha.open("w") as f:
        for r in rows:
            f.write(f"{r['sha256']}  mol_data/{r['filename']}\n")
    print(f"  -> {p_sha}")

    # Console summary
    print(f"\n  {'mol_key':24s} {'tier':>6s} {'q':>3s} {'CAS':>8s} {'basis':>8s} "
          f"{'E0 (Ha)':>13s} {'gap (Ha)':>10s} {'degen':>6s} {'terms':>6s}")
    for r in rows:
        cas = (f"({r['active_electrons']}e,{r['active_orbitals']}o)"
               if r["active_electrons"] else "?")
        print(f"  {r['mol_key']:24s} {r['tier']:>6s} {r['n_qubits']:>3d} {cas:>8s} "
              f"{str(r['basis']):>8s} {r['e0_total_ha']:>13.6f} {r['gap01_ha']:>10.6f} "
              f"{r['gs_degeneracy']:>6d} {r['n_pauli_terms']:>6d}")

    print("\nDone.")


if __name__ == "__main__":
    main()
