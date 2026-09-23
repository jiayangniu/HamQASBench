# HamQASBench reference

HamQASBench provides five QAS implementations, molecular-instance generation,
experiment configurations, and circuit-analysis tools. Start with the
[README](../README.md) for installation and example commands.

## Instances and diagnostic comparisons

The main suite contains eleven Hamiltonians. Code keys use T1–T5; the paper
calls the corresponding diagnostic tasks R1–R5. H4_Chain is reused in the R4
connectivity comparison, so these groups do not count distinct instances twice.

| Code group | Instances | Comparison |
| --- | --- | --- |
| T1 / R1 | BeH2_STO3G, LiH_Equil | Circuit cost at chemical accuracy under shallow and deep budgets |
| T2 / R2 | CH2 | State selection within a degenerate ground subspace |
| T3 / R3 | H2_Stretch, H2O_StrongCorr, H4_Chain | Output and target single-qubit entropy profiles |
| T4 / R4 | H3_Linear and H4_Chain (registered under T3) | All-to-all versus linear connectivity on the same Hamiltonian |
| T5 / R5 | BeH2 at 8, 10, 12, and 14 qubits | A fixed-geometry ladder with varying basis sets and active spaces |

See [data preparation](data_preparation.md) for generation commands and
[instance metadata](../artifact/instances.json) for registered files and settings.
Generated NPZ files store Pauli coefficients, the scalar energy shift, spectral
information, and available molecular metadata. Large instances can use sparse
storage instead of a dense Hamiltonian matrix.

Exact reference energies use the full encoded qubit space. The electron count
used to construct the Hamiltonian does not constrain the sector of its lowest
state. For a degenerate ground level, an entropy profile describes a specified
reference state, not the entire subspace; use the paper's reference-state
conventions when comparing profiles.

## Measurements and saved records

Chemical accuracy is an energy error of at most 1.6 mHa. The paper reports
energy error and success alongside reference-relative gate count, local entropy
mismatch for unique targets, and state diagnostics for degenerate targets.
Gate counts use the common RX/RY/RZ/CNOT evaluation basis.

Success statistics depend on the records being counted. Reinforcement-learning
rollout success rates pool successful and total rollouts at selected checkpoints.
Run success rates for the other methods count selected evaluation circuits.
These denominators must be identified explicitly.

Training records, selected circuits, and post-hoc re-optimized circuits are
different artifacts. RL `best_eval.txt` gate histories omit optimized angles;
re-optimizing them does not recover the original rollout state. The analysis
tools operate on the inputs described in [analysis usage](../analysis/README.md).
This code distribution does not include the paper's per-run experimental data.

### Additional runtime diagnostics

Some runners optionally report CNOT@chem, function-evaluation counts, and policy
circuit diversity (PCD). These are implementation diagnostics, not replacements
for the paper's evaluation protocol. PCD compares states using
`1 - |<psi_i|psi_j>|^2`: `D_struct` fixes rotation angles to pi/4, while `D_func`
uses optimized angles. Neither value alone identifies a cause of search failure.

## Implemented Methods

### RL Methods

| Method | RL Algorithm | Action Space |
|--------|-------------|--------------|
| CRLQAS | DQN (off-policy) | Discrete |
| HyRLQAS / Hybrid\_REINFORCE | Batch REINFORCE (on-policy) | Hybrid discrete+continuous |
| RENEW | REINFORCE + Refine Head | Hybrid discrete+continuous |

### Non-RL Baselines

| Method | Type |
|--------|------|
| QuantumDARTS | Differentiable NAS (ICML 2023) |
| TFQAS | Training-free zero-cost proxy |
| GQEQAS | Generative sequence model (GPT-style autoregressive circuit generation) |

#### QuantumDARTS: nfev accounting

QuantumDARTS has two phases with fundamentally different evaluation semantics:

- **Phase 1 (Architecture Search):** Optimises soft Gumbel-softmax circuits via continuous relaxation.  These are *not* hardware-executable discrete circuits.  Phase 1 nfev is reported separately as `phase1_nfev` and is *not* directly comparable to RL method nfev.
- **Phase 2 (Discrete Evaluation):** Evaluates discrete candidates, including the argmax circuit and sampled choices, and reports `phase2_nfev`. Comparing costs across methods also requires accounting for the optimizer and evaluation batch.

Papers must report Phase 1 and Phase 2 nfev separately to avoid misleading comparisons.

#### GQEQAS: generative autoregressive circuit search

GQEQAS adapts the Generative Quantum Eigensolver (GQE) into the HamQASBench framework.  A GPT-2 style decoder-only transformer (GPTQE) autoregressively generates circuit token sequences; the operator pool serves as the vocabulary.  The model is trained via a **logit-matching loss**: the cumulative sum of chosen-token logits is regressed toward ground-truth prefix energies, teaching the model to assign higher probability to tokens that reduce energy.

Two operator pool types are supported:

| Pool | Vocabulary | Angle handling |
|------|-----------|----------------|
| `primitive` | RX/RY/RZ (fixed π-equal angles) + CNOT pairs | Fixed angles in pool; COBYLA/Rotosolve re-optimises after generation |
| `ucc` | UCCSD excitation operators via PennyLane | Time-evolution angles via logspace schedule |

For the `primitive` pool with `num_op_times = 8`, the rotation angles are `[π/8, π/4, 3π/8, π/2, 5π/8, 3π/4, 7π/8, π]` (π equal divisions).

**Variable-length generation** — `seq_len` is a maximum; actual circuit length is sampled from `Uniform[1, seq_len]` per batch when `length_mode = uniform`.  Shorter sequences are zero-padded in the replay buffer to keep array shapes consistent.

**Training modes:**

| Mode | Description |
|------|-------------|
| `offline` | Pre-builds a random-circuit dataset then trains to convergence |
| `online` | Model generates circuits → evaluate energies → add to replay buffer → train; repeats with temperature annealing |

Post-generation re-optimisation is controlled by `training_reopt` (during training) and `benchmark_reopt` (during eval).

Use `--method gqeqas` to invoke `GQERunner`; configs live under `configs/gqe/`, and results are written to `results/gqeqas/`.

---

## Installation

See the [installation and reproduction guide](../README.md).

## Quick Start

```bash
cd HamQASBench
conda activate psqasbench

# CRLQAS on T1 BeH2, CPU
python main.py --method crlqas --mol T1_BeH2_STO3G_6q --seed 11111 --device cpu

# CRLQAS on T5 BeH2 cc-pVDZ 14q, GPU, parallel envs
python main.py --method crlqas --mol T5_BeH2_CCPVDZ_14q --seed 11111 --device cuda:0

# HyRLQAS (RENEW) on T1 LiH
python main.py --method hyrlqas --mol T1_LiH_Equil_6q --seed 11111 --device cuda:0

# Override config explicitly
python main.py --method crlqas --mol T5_BeH2_CCPVDZ_14q \
               --config Optimizer_EXP/bench_14q_rotosolve_gpu_k10.cfg --seed 11111 --device cuda:0

# Configs can live in subdirectories under configs/<method>/
python main.py --method crlqas --mol T1_BeH2_STO3G_6q \
               --config Depth_EXP/T1_BeH2_STO3G_6q_cobyla_depth10.cfg \
               --seed 11111 --device cuda:0 --use-wandb 0

# QuantumDARTS on T1 BeH2
python main.py --method qdarts --mol T1_BeH2_STO3G_6q --seed 11111 --device cuda:0

# GQEQAS on T1 BeH2 (depth10 reference config)
python main.py --method gqeqas --mol T1_BeH2_STO3G_6q \
               --config Formal_EXP/T1_BeH2_STO3G_6q_depth10.cfg \
               --seed 11111 --device cuda:1

# GQEQAS on T1 LiH
python main.py --method gqeqas --mol T1_LiH_Equil_6q \
               --config Formal_EXP/T1_LiH_Equil_6q_depth50.cfg \
               --seed 11111 --device cuda:1

# GQEQAS on T5 BeH2 14q (large, Rotosolve)
python main.py --method gqeqas --mol T5_BeH2_CCPVDZ_14q \
               --config Formal_EXP/T5_BeH2_CCPVDZ_14q.cfg \
               --seed 11111 --device cuda:3
```

All output is written to:

```text
results/<method>/<mol>/<config_path_without_suffix>/seed<seed>/
```

Example:

```text
results/crlqas/T1_BeH2_STO3G_6q/Depth_EXP/T1_BeH2_STO3G_6q_cobyla_depth10/seed11111/
```

---

## Common Run Tweaks

### CLI flags

```bash
python main.py \
  --method crlqas \
  --mol T1_BeH2_STO3G_6q \
  --config Depth_EXP/T1_BeH2_STO3G_6q_cobyla_depth10.cfg \
  --seed 11111 \
  --device cuda:0 \
  --use-wandb 0 \
  --save-summary-detailed 0
```

Commonly changed flags:

- `--method`: choose benchmark runner (`crlqas`, `hyrlqas`, `qdarts`, `tfqas`, `gqeqas`)
- `--mol`: molecule key from `bench_utils.MOL_FILES`
- `--config`: config file relative to `configs/<method>/`
- `--seed`: random seed; creates a separate `seed<seed>` result directory
- `--device`: `cpu`, `cuda:0`, `cuda:1`, ...
- `--use-wandb 0`: disable Weights & Biases upload; benchmark runs default to `0`
- `--save-summary-detailed 1`: additionally save legacy `summary_<seed>.npy`

If you do enable W&B logging, `WANDB_ENTITY` and `WANDB_PROJECT` can be used to route runs to your own workspace without editing the code.

### Config fields most often edited

```ini
[general]
episodes = 10000
eval_every = 1000
eval_K = 50
num_parallel_envs = 8
use_wandb = 0
save_every = 500

[env]
num_layers = 20
accept_err = 0.0016
connectivity = linear    # all | linear; select the comparison condition

[non_local_opt]
optim_alg = COBYLA
global_iters = 100
```

What they control:

- `general.eval_every`: how often periodic eval runs
- `general.eval_K`: number of rollouts used per eval
- `general.num_parallel_envs`: parallel environments for training
- `env.num_layers`: maximum circuit depth (= maximum episode steps)
- `env.accept_err`: success threshold in Hartree
- `env.connectivity`: `all` or `linear`; R4 compares both settings
- `non_local_opt.optim_alg`: local angle optimizer (`COBYLA`, `Rotosolve`, `SPSA`, `AdamSPSA`, `PSRAdam`)
- `non_local_opt.global_iters`: optimizer budget for `COBYLA`, `SPSA`, `AdamSPSA`, `PSRAdam`
- `non_local_opt.rotosolve_sweeps`: sweep count for `Rotosolve`

---

## Configuration Reference

Config files live under `configs/crlqas/`, `configs/hyrlqas/`, `configs/qdarts/`, `configs/tfqas/`, `configs/gqe/`.

```ini
[general]
episodes = 10000          # total training episodes
eval_every = 1000         # periodic eval interval
eval_K = 20               # rollouts per eval
num_parallel_envs = 10    # 1 = single-env, >1 = parallel training
use_wandb = 0             # benchmark default; set to 1 to enable wandb upload
log_every = 10
save_every = 200

[env]
num_qubits = 14
num_layers = 20           # max circuit depth
accept_err = 0.0016       # chemical accuracy threshold (Ha)
connectivity = all        # all | linear

[problem]
mol_file = <filename>.npz

[agent]
agent_type = DeepQNstep
agent_class = DQN_Nstep
batch_size = 1000

[non_local_opt]
method = scipy_each_step
optim_alg = COBYLA        # COBYLA | Rotosolve | SPSA | AdamSPSA | PSRAdam
global_iters = 100
```

### GQEQAS config reference

```ini
[env]
num_qubits = 6
accept_err = 0.0016               # chemical accuracy threshold (Ha)
analysis_save_threshold = 0.0016  # save circuit snapshots below this energy error
active_electrons = 2              # active-space electrons (must match .npz generation)
active_orbitals = 3               # active-space orbitals (= num_qubits // 2 by default)
connectivity = all                # all | linear

[operator_pool]
pool_kind = primitive             # primitive | ucc
include_minus = 1                 # include ±angle variants (primitive pool only)
num_op_times = 8                  # number of angle discretisation points
# primitive pool: angles = linspace(π/n, π, n)  [π equal divisions]
# ucc pool:       times  = logspace(min_exp, max_exp, n) / divisor
op_time_min_exp = -2.0
op_time_max_exp = 0.0
op_time_divisor = 160.0

[model]
seq_len = 50                      # maximum circuit length (tokens)
length_mode = uniform             # fixed | uniform — uniform draws L ~ Uniform[1, seq_len]
train_size = 1024                 # offline dataset size (offline mode only)
n_layer = 6                       # transformer depth
n_head = 8                        # attention heads
n_embd = 256                      # embedding dimension
dropout = 0.1

[training]
training_mode = online            # offline | online
epochs = 4000
lr = 0.00005
batch_splits = 16                 # gradient accumulation steps (effective batch = train_size / batch_splits per epoch)
eval_every = 200                  # evaluate every N epochs
eval_n_sequences = 100            # sequences generated during each eval
eval_temperature = 0.001          # near-greedy decoding for eval
train_temperature = 1.0           # sampling temperature during training
# online-mode specific
online_sample_count = 128         # fresh circuits generated per refresh
online_refresh_every = 25         # epochs between online data refreshes
online_temperature_final = 0.05   # annealing end temperature
online_temperature_schedule = linear
replay_buffer_size = 2048         # FIFO replay buffer capacity (0 = disabled)
replay_mix_ratio = 0.5            # fraction of batch drawn from replay buffer
warmup_epochs = 400               # epochs of offline pre-training before online loop

[general]
compute_pcd = 0                   # 0 | 1 — compute D_struct / D_func (expensive)
training_reopt = 1                # re-optimise angles after each training-time generation
benchmark_reopt = 1               # re-optimise angles during eval
[non_local_opt]                   # same fields as RLQAS; inherited by training/eval reopt
method = scipy_each_step
optim_alg = COBYLA                # COBYLA | Rotosolve | SPSA | AdamSPSA | PSRAdam
global_iters = 100
n_restarts = 1
# for large molecules (≥ 10q) Rotosolve with batched GPU path is preferred:
# optim_alg = Rotosolve
# rotosolve_sweeps = 2
# global_batched_rotosolve = 1
# parallel_eval_batch_size = 8
```

**Configuration notes:**

- `seq_len` and `length_mode` control the maximum length and how lengths are sampled.
- `warmup_epochs` controls the initial offline-training period.
- `eval_every` and `eval_n_sequences` control evaluation frequency and sample count.
- `replay_buffer_size` and `replay_mix_ratio` control retained training samples.

Use the supplied configuration for the selected method and instance. The fields
above illustrate supported options rather than a common computational budget.

---

## Angle Optimisers

Each environment step runs a local angle optimiser over all current rotation gates.

| Optimiser | Update rule | Budget field | GPU acceleration |
|-----------|-------------|--------------|-----------------|
| `COBYLA` | SciPy derivative-free | `global_iters` | partial |
| `Rotosolve` | Analytic coordinate sweep using `{0, π/2, π}` probes | `rotosolve_sweeps` | strongest |
| `SPSA` | Stochastic gradient from `±delta` probes | `global_iters` | yes |
| `AdamSPSA` | SPSA gradient + Adam-style update | `global_iters` | yes |
| `PSRAdam` | Exact parameter-shift gradient + Adam | `global_iters` | yes |

When `num_parallel_envs > 1`, the runner uses one CUDA stream per environment and overlaps optimiser kernels before a single `synchronize()` barrier.  This grouped path is cleanest for `Rotosolve`, `SPSA`/`AdamSPSA`, and `PSRAdam`.

### Optimizer Field Reference

| Field | Used by | Meaning |
|-------|---------|---------|
| `method` | all | usually `scipy_each_step` |
| `optim_alg` | all | selects the local optimizer |
| `global_iters` | COBYLA, SPSA, AdamSPSA, PSRAdam | iteration budget |
| `rotosolve_sweeps` | Rotosolve | number of full coordinate sweeps |
| `global_batched_rotosolve` | Rotosolve, parallel | enable grouped batched path |
| `global_batched_spsa` | SPSA/AdamSPSA, parallel | enable grouped batched path |
| `global_batched_psr` | PSRAdam, parallel | enable grouped batched path |
| `a`, `alpha`, `c`, `gamma`, `lamda` | SPSA, AdamSPSA | SPSA schedule hyperparameters |
| `beta_1`, `beta_2` | AdamSPSA, PSRAdam | Adam momentum hyperparameters |
| `lr` | PSRAdam | Adam learning rate |

---

## Result Artifacts

Runs write their outputs under:

```text
results/<method>/<mol>/<config>/seed<seed>/
```

For RLQAS methods (`crlqas`, `hyrlqas`), the full training trace is written.  `TFQAS`
and `QuantumDARTS` write compatibility files for post-hoc structure analysis,
with method-specific trace semantics. TFQAS records candidate snapshots as
pseudo-episodes. QuantumDARTS records sampled discrete circuits at evaluation
checkpoints; its step field identifies the training epoch.

Common files you will typically find are:

| File | Contents |
|------|----------|
| `run_meta.txt` | Method, mol, seed, device, exact energy, wall-clock time, final result |
| `episode_summary.tsv` | Per-episode energy, depth, CNOT count, reward, ε |
| `episode_traces.txt` | RL traces or compatibility pseudo-traces; may contain `analysis_snapshots` and/or `gates_direct` |
| `policy_loss.tsv` | Policy gradient / DQN loss per update |
| `best_train.txt` | Circuit achieving the lowest training energy |
| `best_eval.txt` | Best eval checkpoint (SR, CNOT@chem, D\_struct, D\_func) + full eval trend |
| `global_best_state_<seed>.npz` | Saved state tensor and op\_history of the best found circuit |
| `best_thresh*_model.pth` | Policy network checkpoint at global-best energy |
| `config_used.cfg` | Exact config file used (for reproducibility) |

### `episode_traces.txt` format

For RLQAS methods, each episode block may contain fields such as:

```
[episode N]
actions = [...]
energies_ha = [...]
energy_errors_ha = [...]
rewards = [...]
analysis_snapshots = [
  {"step": S, "gate_params": [...], "param_step_indices": [...]},
  ...
]
```

`analysis_snapshots` stores one or more threshold-crossing events.  Each snapshot records the
gate parameters needed for warm-start reconstruction in post-hoc analysis.

For `TFQAS` and `QuantumDARTS`, `episode_traces.txt` is written in a compatibility form:

```
[episode N]
energy_errors_ha = [...]
analysis_snapshots = [{"step": 0, "gates_direct": [...]}]
```

Here `gates_direct` is a direct gate list, so `critical_structure_tool` can reconstruct the
circuit without an RL action dictionary.

---

## Critical Structure Tool

### What it is

`critical_structure_tool` is a post-hoc analysis tool for answering:

> For a given performance regime, which gate sub-structure is actually responsible for the low energy?

It addresses the **puzzle-piece phenomenon** observed in RLQAS training traces: energy stays near the initial value for many steps, then drops sharply when one specific gate is inserted.  The tool identifies and compares these critical substructures across multiple episodes and seeds.

### Scope and prerequisites

The tool works with:

- **RLQAS methods** (`crlqas`, `hyrlqas`, `renew`) using action-based traces
- **direct-gate snapshot methods** (`TFQAS`, `QuantumDARTS`) that export compatibility traces with `gates_direct`

Required files per run directory:

| File | Required | Used for |
|------|---------|---------|
| `episode_traces.txt` | **yes** | RL action traces or direct-gate snapshot events |
| `config_used.cfg` | **yes** | action-id → gate decoding, molecule lookup, optimizer inheritance |
| `run_meta.txt` | optional | fallback `accept_err` / `analysis_save_threshold` when `--target-error-mha` is not specified |

For `TFQAS` and `QuantumDARTS`, the tool analyzes serialized candidate/final circuits rather than an RL trajectory.  These runs are therefore supported for structural pruning, but `episode` index should be interpreted as a method-specific candidate ordering rather than training time.

### Warm-start reconstruction

When `episode_traces.txt` contains parameterized `analysis_snapshots` (produced by runs after the snapshot-logging change), the tool uses the saved optimised angles as the starting point for circuit reconstruction. This substantially improves reconstruction fidelity for branch-sensitive and near-degenerate cases such as `T2_CH2_8q`, where cold-start re-optimisation from angle = 0 can fall into a different basin.

For **old result files** without `analysis_snapshots`, the tool falls back to legacy `first_hit_snapshot` if present, and otherwise to cold-start reconstruction (all angles initialised to 0).

### Usage

Recommended wrapper script:

```bash
cd HamQASBench
conda activate psqasbench

# Interactive: prints bucket summary and prompts for selection
python -m analysis.analyze_critical_structure results/crlqas/T1_BeH2_STO3G_6q/Depth_EXP/T1_BeH2_STO3G_6q_cobyla_depth10

# Direct bucket selection
python -m analysis.analyze_critical_structure \
  results/crlqas/T1_BeH2_STO3G_6q/Depth_EXP/T1_BeH2_STO3G_6q_cobyla_depth10 \
  --bucket 0.55 \
  --select-n 6 \
  --beam-width 4 \
  --branching-factor 3 \
  --prune-budget 1000 \
  --out-dir critical_structure_analysis/t1_beh2_cobyla_d10_bucket055

# Harder 8-qubit case — larger slack, smaller budget
python -m analysis.analyze_critical_structure \
  results/crlqas/T2_CH2_8q/Formal_EXP/T2_CH2_8q_rotosolve_s2_20k \
  --bucket 0.00 \
  --select-n 4 \
  --beam-width 4 \
  --branching-factor 3 \
  --prune-budget 300 \
  --reconstruction-slack-mha 0.5 \
  --out-dir critical_structure_analysis/t2_ch2_8q_bucket000

# Multiple run directories (multi-seed analysis)
python -m analysis.analyze_critical_structure \
  results/crlqas/T1_BeH2_STO3G_6q/Depth_EXP/T1_BeH2_STO3G_6q_cobyla_depth10 \
  results/crlqas/T1_BeH2_STO3G_6q/Depth_EXP/T1_BeH2_STO3G_6q_cobyla_depth10_seed2 \
  --bucket 0.55 --select-n 10 --out-dir critical_structure_analysis/t1_beh2_multiseed
```

Equivalent module entrypoint: `python -m critical_structure_tool <args...>`

### Key parameters

**Episode / bucket selection**

| Flag | Default | Meaning |
|------|---------|---------|
| `--target-error-mha` | inherit from `run_meta.txt` | threshold used to filter saved snapshot events |
| `--bucket` | interactive prompt | snapshot-event error bucket to analyse |
| `--select-n` | 6 | number of representative snapshot events to prune |
| `--late-fraction` | 1/3 | sample from the last fraction of episode indices; for TFQAS/QuantumDARTS this is candidate-order, not RL time |
| `--anchor-top-k` | 3 | most frequent event-time last actions treated as protected anchors |

**Error tolerances**

| Flag | Default | Meaning |
|------|---------|---------|
| `--bucket-slack-mha` | 0.05 | allowed error above bucket center during pruning |
| `--reconstruction-slack-mha` | 0.3 | extra slack when reconstructed baseline differs from trace; increase for branch-sensitive cases such as `T2_CH2_8q` |
| `--delta-tolerance-mha` | 0.2 | maximum single-step error increase for a gate to be deletable |

**Pruning budget**

| Flag | Default | Meaning |
|------|---------|---------|
| `--prune-budget` | 1000 | total child circuit evaluations across the whole pruning phase (main budget) |
| `--beam-width` | 4 | beam states kept after each expansion |
| `--branching-factor` | 3 | top-k deletion candidates expanded per beam state |
| `--max-prune-steps` | auto | depth cap per episode; auto-computed as `gate_count - fixed_gate_count` |

**Optimizer**

| Flag | Default | Meaning |
|------|---------|---------|
| `--analysis-optimizer` | `inherit` | optimizer used during reconstruction and pruning; `inherit` reads from `config_used.cfg` |
| `--cobyla-maxiter` | 300 | COBYLA iteration cap for analysis |
| `--rotosolve-sweeps` | 2 | Rotosolve sweep count for analysis |
| `--n-restarts` | 2 | COBYLA restarts per optimization call |

### Output files

All outputs are written under `--out-dir` (default: `critical_structure_analysis`):

| File | Contents |
|------|----------|
| `first_hit_error_distribution.tsv` | Fine-grained distribution of saved snapshot-event errors |
| `bucket_summary.tsv` | Coarser bucket view with counts and mean event step |
| `anchor_actions.tsv` | Most frequent event-time last actions for the chosen bucket |
| `selected_episodes.tsv` | Snapshot events selected for pruning (episode key, seed, step, last action) |
| `summary.tsv` | Per-snapshot pruning results: baseline error, retained error, gate counts, redundancy |
| `summary.md` | Human-readable markdown table of pruning results |
| `exact_signature_counts.tsv` | Exact retained gate-sequence matches across snapshot events |
| `meta.txt` | Full run metadata (parameters, anchor actions, common retained gates) |

### Interpreting results

**Redundancy ratio** — fraction of gates removed while preserving the error regime.  High redundancy (>70%) is the expected finding for RLQAS due to Circuit Structure Bias.

**Exact retained-structure matches** — episodes retaining identical gate sequences.  Count > 1 suggests a stable learned motif.

**Common retained gate signatures** — gates present in all pruned episodes (exact set intersection).  `none` does not mean no pattern exists; it often indicates consistent qubit-level patterns that the exact-match test misses (use the individual `summary.md` to inspect manually).

**Reconstruction baseline >> target error** — indicates warm-start failure (cold-start landed in the wrong basin). Increase `--reconstruction-slack-mha`, check that `analysis_snapshots` or legacy `first_hit_snapshot` is present in traces, or treat that episode as unusable. This is most common for branch-sensitive cases such as `T2_CH2_8q`, especially with old result files.

---

## Pipeline Overview

```text
Training run (CRLQAS / HyRLQAS / RENEW / TFQAS / QuantumDARTS / GQEQAS)
    │
    ├── results/<method>/<mol>/<config>/seed<seed>/
    │   ├── episode_traces.txt     ← main input for analysis
    │   ├── config_used.cfg        ← gate decoding + optimizer info
    │   └── run_meta.txt           ← threshold fallback
    │
    └── critical_structure_tool
        │
        ├── 1. Discover runs (episode_traces.txt files)
        ├── 2. Expand saved snapshot events
        ├── 3. Build event-error distribution
        ├── 4. Choose bucket interactively or via --bucket
        ├── 5. Sample representative snapshot events
        ├── 6. Reconstruct circuit from actions or gates_direct
        │       warm-start: use analysis_snapshots angles when available
        │       legacy fallback: use first_hit_snapshot if present
        │       cold-start: re-optimize from angle=0 if no snapshot exists
        ├── 7. One-shot gate importance (delete each gate, measure |ΔE|)
        ├── 8. Beam search pruning (fixed deletion prior, prune-budget)
        └── 9. Compare retained structures across snapshot events
```

---
