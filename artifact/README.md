# Reproduction metadata

This directory contains only small, reviewable reference metadata:

- `instances.csv` / `instances.json`: 11 main T1–T5 instances and two optional
  legacy extensions, with Hamiltonian metadata and original-file hashes.
- `mol_data.sha256`: checksums of the 13 original NPZ files, using repo-relative paths.
- `gen_manifest.py`: regeneration from locally available registered Hamiltonians.

The binaries themselves, experiment outputs, and machine-specific environment
exports are not included. Install with [`environment.yml`](../environment.yml)
and follow [data preparation](../docs/data_preparation.md). Legacy entries with
unknown active-space/basis fields are explicitly incomplete; no missing values
have been inferred. The generator overwrites manifests, so preserve the reference
files separately when comparing regenerated data.
