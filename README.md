# HamQASBench

A reproducible benchmark for quantum architecture search, with a shared molecular
suite, runner interface, evaluation metrics, and circuit-structure diagnostics.
The `psqasbench` environment name and `PSQAS_RESULTS_DIR` variable are retained
for compatibility with existing installations.

This repository contains the benchmark reproduction code and selected analysis
tools. It does not bundle experiment outputs, checkpoints, or Hamiltonian binaries.

## Repository layout

| Path | Purpose |
| --- | --- |
| `main.py`, `bench_utils.py` | Unified launcher, molecule registry, config selection |
| `RLQAS/`, `QuantumDARTS/`, `TFQAS/`, `GQEQAS/` | Five benchmark methods |
| `configs/` | Formal runs and depth, optimizer, connectivity/operator-pool ablations |
| `metrics/` | Shared evaluation and circuit-diversity metrics |
| `mol_gen/` | Core molecule generation and fingerprint calculations |
| `analysis/` | Chemical-accuracy, pruning, entropy, fidelity, gate-bias and circuit plots |
| `critical_structure_tool/` | Reusable circuit reconstruction and pruning package |
| `artifact/` | Small reproduction manifests and original-file checksums |
| `scripts/summarize_optimizer_exp.py` | Optimizer comparison summary |
| `docs/` | Detailed benchmark/configuration and data-generation reference |

## Install

The supplied environment targets Linux with Python 3.10. It records direct package versions
observed in the benchmark environment; it omits machine-specific Conda build IDs,
CUDA library exports, and absolute installation prefixes.

```bash
conda env create -f environment.yml
conda activate psqasbench
python main.py --help
python -m unittest discover -s tests -v
```

The default `qulacs` installation supports CPU simulation. A CUDA-enabled PyTorch
installation and a separately GPU-enabled Qulacs build are needed for their GPU
paths. Start with `--device cpu`; a CUDA PyTorch device alone does not make a
CPU-only Qulacs build GPU-enabled. The launcher limits CPU library threads to one
per process, matching the retained experiment setup.

On older Linux clusters, if NumPy reports a missing `GLIBCXX` symbol after Torch
loads, select the Conda C++ runtime before launching Python:

```bash
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib:${LD_LIBRARY_PATH:-}"
```

## Prepare Hamiltonians

The main suite comprises **11 T1–T5 instances**. The manifest also lists two
legacy extensions (`H2O_10q`, `LiH_12q`); those are optional and are not configured
for HyRLQAS. See [data preparation](docs/data_preparation.md) for the exact
commands, active spaces, reference hashes, and legacy-data limitations.

Generate T1–T4 with:

```bash
python mol_gen/prepare_molecules.py
```

Files go in `mol_data/`. They are excluded from Git, as are generated outputs.
For existing archived data, place or symlink the files under that directory.
A fresh clone needs this data-preparation step before training.

## Run a benchmark

Run commands from the repository root. `--device` and `--seed` are required.
The method-specific formal configuration is selected automatically unless
`--config` is supplied.

```bash
python main.py --method crlqas --mol T1_BeH2_STO3G_6q --seed 11111 --device cpu --use-wandb 0
python main.py --method hyrlqas --mol T1_LiH_Equil_6q --seed 11111 --device cpu --use-wandb 0
python main.py --method qdarts --mol T1_BeH2_STO3G_6q --seed 11111 --device cpu
python main.py --method tfqas --mol T1_BeH2_STO3G_6q --seed 11111 --device cpu
python main.py --method gqeqas --mol T1_BeH2_STO3G_6q --seed 11111 --device cpu
```

These are full experiments, not short smoke tests. Formal configurations can be
expensive. Results follow
`results/<method>/<molecule>/<config-without-suffix>/seed<seed>/`.
Set `--results-root /path/to/data-disk/results` or `PSQAS_RESULTS_DIR` to store
large outputs elsewhere. W&B logging is disabled by default.

Keep the config, seed, `run_meta.txt`, traces and exported circuits together.
Different methods persist different circuit stages: RL global-best state tensors
represent training-best circuits; RL `best_eval.txt` gate histories omit angles.
Re-optimizing those histories is a separate post-hoc calculation, not recovery
of the original evaluation state.

## Analyze results

Analysis entrypoints are grouped under `analysis/` and invoked as modules.
See [analysis usage](analysis/README.md) and the
[critical-structure guide](critical_structure_tool/README.md).
The historical `python analyze_critical_structure.py ...` launcher remains valid.

```bash
python -m analysis.analyze_chem_accuracy_hits results/crlqas/T1_BeH2_STO3G_6q/Formal_EXP/T1_BeH2_STO3G_6q_cobyla_20k_depth10/seed11111
python -m critical_structure_tool --help
python -m analysis.analyze_fidelity --help
python -m analysis.analyze_entropy --help
```

The [full benchmark reference](docs/benchmark_reference.md) describes metrics,
configuration fields, method-specific accounting and saved artifacts.

## Files and outputs

Source code, configurations, documentation, and instance metadata are tracked in
Git. Generated Hamiltonians, run outputs, figures, and checkpoints are stored
locally and are not included in this repository. See
[data preparation](docs/data_preparation.md) for generating the main suite.
