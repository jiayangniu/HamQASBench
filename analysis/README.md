# Selected benchmark analyses

Run from the repository root as `python -m analysis.<name>`. The selected iona scripts were
moved here with repository-relative paths adjusted. The T3 plot helper includes
the existing iona PDF/PNG rendering update; benchmark algorithms and numerical
analysis calculations are unchanged.

| Module | Input / purpose |
| --- | --- |
| `analyze_chem_accuracy_hits` | A run directory: first chemical-accuracy hits and action frequencies |
| `analyze_critical_structure` | Saved run traces: select error buckets and prune circuits; also `python -m critical_structure_tool` |
| `analyze_fidelity` | Pruning output directories: re-optimize retained circuits and compare state fidelity |
| `analyze_entropy` | Pruning output directories: single-qubit entropy diagnostics |
| `analyze_late_gate_bias` | Run directories: late-training action/gate biases |
| `plot_fidelity_cluster_progress` | Fidelity-analysis output: cluster progress plots |
| `plot_tier3_representative_circuits` | Selected historical CST summary TSVs: representative T3 figures |

All modules except the final fixed-input paper-figure script support `--help`.
The pruning workflow and parameters are described in
[`critical_structure_tool/README.md`](../critical_structure_tool/README.md).
Run pruning before fidelity/entropy, and fidelity before cluster plotting.

`plot_tier3_representative_circuits` expects the historical subdirectories and
selected episode keys named in its `main()` function under
`critical_structure_analysis/`. Those generated TSVs are deliberately excluded
from Git. It is a paper-figure helper, not an analysis for arbitrary new seeds;
use fresh pruning summaries and update the selection explicitly for new runs.

Generated figures, CSV/TSV tables and pruning outputs stay outside version control.
Re-optimized pruned circuits are post-hoc diagnostics. They should not be reported
as the original evaluation-time state or as extra benchmark success samples.
