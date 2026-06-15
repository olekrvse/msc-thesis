# Robust Governance for Orbital Congestion in Low Earth Orbit

Simulation code and results accompanying my MSc thesis at Rotterdam School
of Management (RSM), Erasmus University. The project uses
[pySSEM](https://github.com/ARCLab-MIT/pyssem) — an open-source source-sink
evolutionary model of the Low Earth Orbit (LEO) debris environment — to run
a 192-scenario factorial campaign comparing four categories of governance
intervention (command-and-control, market-based, liability/enforcement, and
coordination/space traffic management) under uncertainty in launch growth,
atmospheric drag, and operator behavioural compliance.

The full thesis manuscript will be available via the Erasmus University
thesis repository ([thesis.eur.nl](https://thesis.eur.nl/)) after graduation.

## Key finding

Post-mission disposal compliance dominates every other governance lever by
roughly an order of magnitude: sweeping it across its plausible range moves
end-of-century debris by a factor of ~7, while coordination/space traffic
management instruments (collision avoidance, orbital slotting) are
environmentally inert at the population scale — useful operationally, but
they do not reduce the debris stock that drives long-run congestion.

## Repository structure

```
.
├── configs/
│   └── baseline.json              # pySSEM scenario config (40 shells, 200-1200 km, BDF integrator)
├── exploration/
│   ├── 01_baseline_run.py         # first baseline pySSEM run (early exploration)
│   ├── 02_pm_sensitivity.py       # quick Pm sweep (early exploration)
│   ├── sensitivity_sweep.py       # single-parameter sweeps (Pm, alpha, slotting, deltat, launch)
│   ├── 02_combination_tests.py    # parameter combination tests + per-satellite collision risk
│   ├── 03_formal_campaign.py      # main driver: 192-run governance campaign
│   ├── 04_fix_outputs.py          # trajectory re-runs, low-solar summary, robustness-ranking figure
│   ├── 05_thesis_figures_ch5.py   # final Ch.5 figures + campaign design schematic
│   └── gen_thesis_figures.py      # conceptual framework + pySSEM schematic diagrams
├── results/                        # CSV / markdown outputs (campaign + sensitivity summaries)
├── figures/                         # generated plots (sensitivity, campaign, thesis figures)
├── dashboard/
│   └── governance_explorer.html   # standalone interactive results explorer
├── pyssem/utils/launch/data/       # pySSEM input data (NOT committed, see Data section)
├── simple-tables.lua                # pandoc filter used when building the thesis document
├── requirements.txt
└── LICENSE
```

## Setup

1. Clone this repository and create a virtual environment:

   ```bash
   git clone https://github.com/olekrvse/msc-thesis.git
   cd thesis-leo
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install the Python dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Install pySSEM from its upstream repository. The scripts expect it at
   `./pyssem-repo` (they add this path via `sys.path.insert`):

   ```bash
   git clone https://github.com/ARCLab-MIT/pyssem.git pyssem-repo
   pip install -e ./pyssem-repo
   ```

4. Obtain the pySSEM launch data (see [Data](#data) below) and place it at:

   ```
   pyssem/utils/launch/data/ref_scen_SEP2.csv
   pyssem/utils/launch/data/x0.csv
   ```

5. Link the atmospheric drag data bundled with pySSEM (precomputed density
   lookup tables) into the same `pyssem/utils/` layout:

   ```bash
   ln -s ../../pyssem-repo/pyssem/utils/drag pyssem/utils/drag
   ```

## How to reproduce

Run from the repository root. Scripts are numbered in the order they were
developed; the dependency order for reproducing the thesis results is:

| Step | Script | Produces |
|---|---|---|
| 1 | `python3 exploration/sensitivity_sweep.py` | `results/parameter_sensitivity_summary.csv`, `figures/sensitivity/*_sensitivity*.png`, tornado chart |
| 2 | `python3 exploration/02_combination_tests.py` | `results/combination_tests.csv`, `figures/sensitivity/combinations_comparison.png`, `alpha_collision_risk.png` |
| 3 | `python3 exploration/03_formal_campaign.py` | `results/formal_campaign.csv`, `results/campaign_summary.csv` — the 192-run campaign (checkpointed and resumable; this is the long-running step) |
| 4 | `python3 exploration/04_fix_outputs.py` | `results/campaign_summary_lowsolar.csv`, `results/trajectory_timeseries.csv`, `figures/campaign/*.png` (heatmaps, vulnerability maps, threshold/robustness-ranking figures). Use `--skip-runs` to reuse a cached trajectory CSV instead of re-simulating. |
| 5 | `python3 exploration/05_thesis_figures_ch5.py` | `figures/thesis/fig_5_1_pm_sweep.png`, `fig_5_2_best_vs_worst.png`, `fig_5_4_behavioral_faultline.png`, `fig_4_2_campaign_design.png` |
| 6 | `python3 exploration/gen_thesis_figures.py` | `figures/thesis/fig_3_1_conceptual_framework.png`, `fig_4_2_pyssem_schematic.png` |

`01_baseline_run.py` and `02_pm_sensitivity.py` are early exploratory scripts
(superseded by `sensitivity_sweep.py`) kept for provenance; they are not part
of the reproduction chain above.

## Data

The two large pySSEM input files are **not committed** to this repository
(309 MB and 4.8 MB respectively, exceeding GitHub's file-size limits):

- `pyssem/utils/launch/data/ref_scen_SEP2.csv` — the SEP2 launch scenario
  (historical + projected launch traffic)
- `pyssem/utils/launch/data/x0.csv` — initial orbital population

Both are inputs to pySSEM's launch model, not outputs of this project's code.
Obtain them via pySSEM's own data pipeline / documentation
(`pyssem-repo/pyssem/utils/launch/`) and place them at the paths above before
running step 3 onward.

All campaign results (`results/*.csv`) and figures (`figures/**/*.png`) ARE
committed, so the analysis is browsable without re-running the simulations.

## Dashboard

[`dashboard/governance_explorer.html`](dashboard/governance_explorer.html) is
a self-contained, dependency-free interactive explorer over the full 192-run
campaign dataset — open it directly in a browser (no server required).

## Citation

If you use this code or data, please cite:

```
Ole Kruse (2026). Orbital Congestion Governance in LEO: A Robustness
Analysis of Governance Categories under Uncertainty. MSc Thesis,
Rotterdam School of Management, Erasmus University.
```

## License

This project's code and results are released under the [MIT License](LICENSE).

pySSEM itself is a separate project (MIT licensed, © Indigo Brownhall /
ARCLab-MIT) and is not included in this repository — see
[Setup](#setup) for how to obtain it.
