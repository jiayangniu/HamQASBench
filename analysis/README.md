# Selected benchmark analyses

Run from the repository root as `python -m analysis.<name>`. These tools read
saved run traces and pruning outputs to analyze circuit cost and prepared states.

| Module | Input / purpose |
| --- | --- |
| `analyze_chem_accuracy_hits` | A run directory: first chemical-accuracy hits and action frequencies |
| `analyze_critical_structure` | Saved run traces: select error buckets and prune circuits; also `python -m critical_structure_tool` |
| `analyze_fidelity` | Pruning output directories: re-optimize retained circuits and compare state fidelity |
| `analyze_entropy` | Pruning output directories: single-qubit entropy diagnostics |
| `analyze_late_gate_bias` | Run directories: late-training action/gate biases |
| `plot_fidelity_cluster_progress` | Fidelity-analysis output: cluster progress plots |

All listed modules support `--help`.
The pruning workflow and parameters are described in
[`critical_structure_tool/README.md`](../critical_structure_tool/README.md).
Run pruning before fidelity/entropy, and fidelity before cluster plotting.

Generated figures, CSV/TSV tables and pruning outputs stay outside version control.
Re-optimized pruned circuits are post-hoc diagnostics. They should not be reported
as the original evaluation-time state or as extra benchmark success samples.
