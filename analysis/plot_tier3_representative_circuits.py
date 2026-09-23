"""Draw publication-quality circuit diagrams for the Tier-3 CST representative circuits.

Reads retained gate sequences directly from the CST summary TSV files and generates:
  - figures/T3_H2Stretch_convergent_pair.pdf  — 2-panel: two seeds, same 6-gate structure
  - figures/T3_H2Stretch_minimal.pdf          — single: ep6934 minimal circuit
  - figures/T3_H2O_best_pruned.pdf            — single: ep11992 19-gate best pruned circuit

Run:
    conda run -n psqasbench python -m analysis.plot_tier3_representative_circuits
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch
    HAS_MPL = True
except Exception:
    HAS_MPL = False

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_DIR = ROOT / "critical_structure_analysis"
FIG_DIR = ROOT / "figures"
FIG_DIR.mkdir(exist_ok=True)

# ─── Gate rendering constants ─────────────────────────────────────────────────
ROT_COLORS = {"RX": "#4CAF50", "RY": "#FFA500", "RZ": "#2CA8E0"}
COLOR_CNOT = "#8E24AA"
BG_EVEN    = "#EEF1FF"
BG_ODD     = "#F7F9FF"

SINGLE_RE = re.compile(r"^(RX|RY|RZ)\(q=(\d+)\)$")
CNOT_RE   = re.compile(r"^CNOT\((\d+)->(\d+)\)$")


# ─── Data loading ─────────────────────────────────────────────────────────────

def load_summary(tsv_path: Path) -> dict[str, dict]:
    rows = {}
    with tsv_path.open() as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            rows[row["episode_key"]] = row
    return rows


def parse_gate_string(gate_str: str) -> list[str]:
    """Split a '|'-delimited retained_gates string into individual tokens."""
    return [tok.strip() for tok in gate_str.split("|") if tok.strip()]


# ─── Layer scheduling ─────────────────────────────────────────────────────────

def _touched(token: str) -> tuple[int, ...]:
    m = SINGLE_RE.match(token)
    if m:
        return (int(m.group(2)),)
    m = CNOT_RE.match(token)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    raise ValueError(f"Unknown gate token: {token!r}")


def assign_layers(tokens: list[str]) -> list[dict[str, Any]]:
    """Greedy left-to-right layer scheduling: each gate goes to the earliest
    layer where none of its qubits are occupied."""
    last: dict[int, int] = {}
    ops: list[dict[str, Any]] = []
    for tok in tokens:
        qubits = _touched(tok)
        layer = max((last.get(q, -1) for q in qubits), default=-1) + 1
        for q in qubits:
            last[q] = layer
        m = SINGLE_RE.match(tok)
        if m:
            ops.append({"type": "rot", "layer": layer,
                        "q": int(m.group(2)), "axis": {"RX":1,"RY":2,"RZ":3}[m.group(1)]})
        else:
            m2 = CNOT_RE.match(tok)
            ops.append({"type": "cnot", "layer": layer,
                        "ctrl": int(m2.group(1)), "targ": int(m2.group(2))})
    return ops


# ─── Drawing primitives ───────────────────────────────────────────────────────

def _y(q: int, n: int) -> float:
    """q=0 on top (matplotlib y increases upward)."""
    return float(n - 1 - q)


def _n_qubits(ops: list[dict]) -> int:
    mx = -1
    for op in ops:
        if op["type"] == "rot":
            mx = max(mx, op["q"])
        else:
            mx = max(mx, op["ctrl"], op["targ"])
    return mx + 1


def _n_layers(ops: list[dict]) -> int:
    return max(op["layer"] for op in ops) + 1 if ops else 1


def draw_rot(ax, x: float, y: float, label: str, alpha: float = 1.0) -> None:
    patch = FancyBboxPatch(
        (x - 0.31, y - 0.22), 0.62, 0.44,
        boxstyle="round,pad=0.02,rounding_size=0.06",
        facecolor=ROT_COLORS[label],
        edgecolor="black", linewidth=1.4, alpha=alpha, zorder=3,
    )
    ax.add_patch(patch)
    ax.text(x, y, label, ha="center", va="center", fontsize=9, weight="bold",
            color="white" if label != "RZ" else "#1a1a1a", zorder=4, alpha=1.0)


def draw_cnot(ax, x: float, yc: float, yt: float, alpha: float = 1.0) -> None:
    ax.plot([x, x], [yc, yt], color=COLOR_CNOT, lw=2.0, zorder=2, alpha=alpha)
    ax.plot(x, yc, "o", color=COLOR_CNOT, ms=6, zorder=3, alpha=alpha)
    ax.plot(x, yt, "o", mfc="white", mec=COLOR_CNOT, ms=10, mew=2.0, zorder=3, alpha=alpha)
    ax.plot([x - 0.11, x + 0.11], [yt, yt], color=COLOR_CNOT, lw=1.8, zorder=4, alpha=alpha)
    ax.plot([x, x], [yt - 0.11, yt + 0.11], color=COLOR_CNOT, lw=1.8, zorder=4, alpha=alpha)


def render_circuit(
    ax,
    ops: list[dict[str, Any]],
    title: str = "",
    subtitle: str = "",
    show_qubit_labels: bool = True,
    show_layer_labels: bool = True,
) -> None:
    n = _n_qubits(ops)
    nl = _n_layers(ops)

    # background stripes
    for l in range(nl):
        ax.axvspan(l - 0.5, l + 0.5, color=BG_EVEN if l % 2 == 0 else BG_ODD, zorder=0)

    # qubit wires
    for q in range(n):
        y = _y(q, n)
        ax.plot([-0.5, nl - 0.5], [y, y], color="black", lw=1.4, zorder=1)
        if show_qubit_labels:
            ax.text(-0.65, y, f"q{q}", ha="right", va="center",
                    fontsize=10, family="monospace")

    # layer labels
    if show_layer_labels:
        for l in range(nl):
            ax.text(l, n - 0.25, f"L{l}", ha="center", va="bottom",
                    fontsize=8, color="#505050")

    # gates
    by_layer: dict[int, list] = defaultdict(list)
    for op in ops:
        by_layer[op["layer"]].append(op)

    for l, layer_ops in by_layer.items():
        for op in layer_ops:
            x = float(l)
            if op["type"] == "rot":
                label = {1: "RX", 2: "RY", 3: "RZ"}[op["axis"]]
                draw_rot(ax, x, _y(op["q"], n), label)
            else:
                draw_cnot(ax, x, _y(op["ctrl"], n), _y(op["targ"], n))

    ax.set_xlim(-0.5 - 0.55, nl - 0.5 + 0.3)
    ax.set_ylim(-0.7, n - 0.05 + 0.45)
    ax.axis("off")
    if title:
        ax.set_title(title, fontsize=13, pad=8, weight="bold")
    if subtitle:
        ax.text(0.0, -0.08, subtitle, transform=ax.transAxes,
                ha="left", va="top", fontsize=9, color="#4d5560")


# ─── Legend helper ─────────────────────────────────────────────────────────────

def add_gate_legend(fig, ax) -> None:
    handles = [
        plt.Rectangle((0, 0), 1, 1, fc=ROT_COLORS["RX"], ec="black", lw=1),
        plt.Rectangle((0, 0), 1, 1, fc=ROT_COLORS["RY"], ec="black", lw=1),
        plt.Rectangle((0, 0), 1, 1, fc=ROT_COLORS["RZ"], ec="black", lw=1),
        plt.Line2D([0], [0], color=COLOR_CNOT, lw=2,
                   marker="o", mec=COLOR_CNOT, mfc="white", ms=7),
    ]
    labels = ["RX rotation", "RY rotation", "RZ rotation", "CNOT"]
    ax.legend(handles, labels, frameon=False, loc="lower center",
              bbox_to_anchor=(0.5, -0.18), ncol=4, fontsize=9)


# ─── Figure generators ────────────────────────────────────────────────────────

def figure_h2stretch_pair(rows: dict[str, dict]) -> None:
    """2-panel: ep6934 (seed33333) and ep7974 (seed33333).
    Both independently found a 6-gate near-exact circuit.
    """
    specs = [
        (
            "crlqas__L4_H2_Stretch_4q__L4_H2_Stretch_4q_cobyla_20k__seed33333__ep6934__snap0",
            "Seed 33333 · Ep 6934",
        ),
        (
            "crlqas__L4_H2_Stretch_4q__L4_H2_Stretch_4q_cobyla_20k__seed33333__ep7974__snap0",
            "Seed 33333 · Ep 7974",
        ),
    ]

    fig, axes = plt.subplots(1, 2, figsize=(11, 3.4))
    fig.suptitle(
        "CRLQAS on T3 H₂-Stretch (4q): Two Episodes Independently Find the Same 6-Gate Minimal Circuit",
        fontsize=13, weight="bold", y=1.01,
    )

    for ax, (key, panel_title) in zip(axes, specs):
        row = rows[key]
        tokens = parse_gate_string(row["retained_gates"])
        ops = assign_layers(tokens)
        error_mha = float(row["retained_error_mha"])
        n_gates = int(row["retained_gate_count"])
        subtitle = f"{n_gates} gates  ·  error = {error_mha:.4f} mHa  ·  {row['resolved_optimizer'].upper()}"
        render_circuit(ax, ops, title=panel_title, subtitle=subtitle)

    add_gate_legend(fig, axes[-1])
    fig.tight_layout()
    out = FIG_DIR / "T3_H2Stretch_convergent_pair.pdf"
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] {out}")
    out_png = out.with_suffix(".png")
    fig2, axes2 = plt.subplots(1, 2, figsize=(11, 3.4))
    fig2.suptitle(
        "CRLQAS on T3 H₂-Stretch (4q): Two Episodes Independently Find the Same 6-Gate Minimal Circuit",
        fontsize=13, weight="bold", y=1.01,
    )
    for ax, (key, panel_title) in zip(axes2, specs):
        row = rows[key]
        tokens = parse_gate_string(row["retained_gates"])
        ops = assign_layers(tokens)
        error_mha = float(row["retained_error_mha"])
        n_gates = int(row["retained_gate_count"])
        subtitle = f"{n_gates} gates  ·  error = {error_mha:.4f} mHa  ·  {row['resolved_optimizer'].upper()}"
        render_circuit(ax, ops, title=panel_title, subtitle=subtitle)
    add_gate_legend(fig2, axes2[-1])
    fig2.tight_layout()
    fig2.savefig(out_png, dpi=300, bbox_inches="tight")
    plt.close(fig2)
    print(f"[OK] {out_png}")


def figure_h2stretch_minimal(rows: dict[str, dict]) -> None:
    """Single best minimal circuit: ep6934 (6 gates, ~0 mHa)."""
    key = "crlqas__L4_H2_Stretch_4q__L4_H2_Stretch_4q_cobyla_20k__seed33333__ep6934__snap0"
    row = rows[key]
    tokens = parse_gate_string(row["retained_gates"])
    ops = assign_layers(tokens)
    error_mha = float(row["retained_error_mha"])
    n_gates = int(row["retained_gate_count"])
    orig_gates = int(row["original_gate_count"])
    redundancy = float(row["redundancy_ratio_pct"])

    fig, ax = plt.subplots(figsize=(6.5, 2.8))
    subtitle = (
        f"{n_gates} retained / {orig_gates} original gates  ·  "
        f"{redundancy:.0f}% redundancy removed  ·  error = {error_mha:.4f} mHa"
    )
    render_circuit(
        ax, ops,
        title="CRLQAS · T3 H₂-Stretch (4q) · Minimal Retained Circuit",
        subtitle=subtitle,
    )
    add_gate_legend(fig, ax)
    fig.tight_layout()
    for ext in (".pdf", ".png"):
        out = (FIG_DIR / "T3_H2Stretch_minimal").with_suffix(ext)
        fig.savefig(out, dpi=300, bbox_inches="tight")
        print(f"[OK] {out}")
    plt.close(fig)


def figure_h2o_best(rows: dict[str, dict]) -> None:
    """Best pruned H2O circuit: seed33333 ep11992 (19 gates, 5.87 mHa).
    Shows circuit-structure bias: many repeated CNOTs remain after pruning.
    """
    key = (
        "crlqas__L4_H2O_StrongCorr_8q__"
        "L4_H2O_StrongCorr_8q_rotosolve_s2_20k__seed33333__ep11992__snap0"
    )
    row = rows[key]
    tokens = parse_gate_string(row["retained_gates"])
    ops = assign_layers(tokens)
    error_mha = float(row["retained_error_mha"])
    n_gates = int(row["retained_gate_count"])
    orig_gates = int(row["original_gate_count"])
    redundancy = float(row["redundancy_ratio_pct"])

    fig, ax = plt.subplots(figsize=(12.5, 5.0))
    subtitle = (
        f"{n_gates} retained / {orig_gates} original gates  ·  "
        f"{redundancy:.0f}% redundancy removed  ·  error = {error_mha:.4f} mHa  ·  "
        "repeated CNOTs reflect circuit-structure bias"
    )
    render_circuit(
        ax, ops,
        title="CRLQAS · T3 H₂O StrongCorr (8q) · Best Pruned Circuit (seed33333)",
        subtitle=subtitle,
    )
    add_gate_legend(fig, ax)
    fig.tight_layout()
    for ext in (".pdf", ".png"):
        out = (FIG_DIR / "T3_H2O_best_pruned").with_suffix(ext)
        fig.savefig(out, dpi=300, bbox_inches="tight")
        print(f"[OK] {out}")
    plt.close(fig)


# ─── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    if not HAS_MPL:
        raise RuntimeError("matplotlib is required. Run: pip install matplotlib")

    h2s_rows = load_summary(ANALYSIS_DIR / "tier3_h2_stretch" / "summary.tsv")
    h2o_rows = load_summary(ANALYSIS_DIR / "tier3_h2o" / "summary.tsv")

    figure_h2stretch_pair(h2s_rows)
    figure_h2stretch_minimal(h2s_rows)
    figure_h2o_best(h2o_rows)

    print(f"\nAll figures saved under: {FIG_DIR}/")


if __name__ == "__main__":
    main()
