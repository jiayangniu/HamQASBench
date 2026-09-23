# Hamiltonian data preparation

Run from the repository root after installing `environment.yml`. All benchmark
filenames are registered in `bench_utils.py`; historical `L*` filenames remain
valid for the public `T*` keys. Generated Hamiltonians are not versioned.

## T1–T4: seven instances

```bash
python mol_gen/prepare_molecules.py
```

This uses the geometries and active spaces embedded in the generator, including
cationic H3 for T4. It writes to `mol_data/` and diagonalizes the full encoded
Hamiltonian. Re-running generation may replace files; use a fresh checkout or
empty data directory when preserving an existing dataset.

## T5: four BeH2 basis/active-space cases

The historical standalone `prepare_beh2_basis_series.py` entrypoint searches for
one 14-qubit case. To reproduce the complete T5 ladder, call its generation
function with each explicit specification:

```bash
python - <<'PY'
from mol_gen.prepare_beh2_basis_series import generate_beh2_case
for basis, electrons, orbitals in [
    ('6-31g', 2, 4),
    ('6-311g', 2, 5),
    ('cc-pvdz', 2, 6),
    ('cc-pvdz', 4, 7),
]:
    generate_beh2_case(basis=basis, active_electrons=electrons,
                      active_orbitals=orbitals, save_eigvals=True)
PY
```

The 14-qubit Hamiltonian is large; allow several GB of memory and disk space.
Inspect `artifact/instances.json` for the reference file sizes. Use a data-disk
symlink for `mol_data/` if necessary. Do not run expensive generation merely to
check whether the package imports correctly.

## Optional legacy extensions

`H2O_10q` and `LiH_12q` configs and reference checksums are preserved for CRLQAS,
QuantumDARTS, TFQAS and GQEQAS. Their archived files do not record sufficient
basis/active-space provenance to claim a complete regeneration recipe here.
Their unknown fields are left null in the manifest. These optional runs require
the original archived NPZ files; the seven-plus-four commands above reproduce
the documented main suite only.

## Checksums and metadata

For original archived files, from the repository root:

```bash
sha256sum -c artifact/mol_data.sha256
```

This checks all 13 entries, so it reports the two legacy files missing if only
the main suite is installed. The hashes identify the original bytes; regeneration
can differ in NPZ metadata, eigensolver details and floating-point representation.
A hash mismatch for regenerated files is not by itself a physical comparison.
Compare active spaces, basis, geometry, Pauli terms and energies explicitly; no
cross-environment numerical tolerance is certified by this release.

`python artifact/gen_manifest.py` regenerates the manifest from locally present
registered files. Run it in a separate copy if preserving the reference manifest:
it overwrites the three manifest files. Fingerprint tools are
`mol_gen/read_fingerprints.py` and `mol_gen/read_fingerprints_beh2_basis.py`.
