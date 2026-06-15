"""
Parameter sensitivity sweep for thesis governance analysis.
Varies Pm, alpha, slotting_effectiveness, deltat, and launch rate one at a time
against the baseline config, saves per-parameter comparison plots, summary CSV,
and a tornado chart.

Run from thesis-leo/ root:
    python3 exploration/sensitivity_sweep.py [param_name]

    param_name (optional): one of pm, alpha, slotting, deltat, launch
    If omitted, all sweeps run in sequence.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'pyssem-repo'))

import json, copy, time, argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from pyssem.model import Model

# ── Config ──────────────────────────────────────────────────────────────────
BASE_CONFIG   = 'configs/baseline.json'
FIGURES_DIR   = 'figures/sensitivity'
RESULTS_DIR   = 'results'
SIM_DURATION  = 100   # years
SIM_STEPS     = 200   # output steps (every 6 months)

os.makedirs(FIGURES_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# ── Parameter sweep definitions ──────────────────────────────────────────────
SWEEPS = {
    'pm': {
        'label':      'Pm (PMD effectiveness)',
        'param':      'Pm',
        'species':    'S',
        'values':     [0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99],
        'log_x':      False,
        'filename':   'pm_sensitivity',
    },
    'alpha': {
        'label':      'α (CA failure rate)',
        'param':      'alpha',
        'species':    'S',
        'values':     [1e-2, 1e-3, 1e-4, 1e-5, 1e-6],
        'log_x':      True,
        'filename':   'alpha_sensitivity',
    },
    'slotting': {
        'label':      'Slotting effectiveness',
        'param':      'slotting_effectiveness',
        'species':    'S',
        'values':     [0.0, 0.25, 0.5, 0.75, 1.0],
        'log_x':      False,
        'filename':   'slotting_sensitivity',
        'extra_params': {'slotted': True},
    },
    'deltat': {
        'label':      'Δt if PMD fails (years)',
        'param':      'deltat',
        'species':    'S',
        'values':     [5, 8, 12, 15, 25],
        'log_x':      False,
        'filename':   'deltat_sensitivity',
    },
    'launch': {
        'label':      'Launch rate (× baseline)',
        'param':      None,          # handled separately via lambda_funs scaling
        'species':    'S',
        'values':     [0.5, 1.0, 1.5, 2.0, 3.0],
        'log_x':      False,
        'filename':   'launch_sensitivity',
        'is_launch_scale': True,
    },
}

# ── Colour palette ────────────────────────────────────────────────────────────
CMAP = cm.get_cmap('viridis')


def load_base_config():
    with open(BASE_CONFIG) as f:
        cfg = json.load(f)
    # Override for sensitivity sweep: longer run, no indicator slow-path
    cfg['scenario_properties']['simulation_duration'] = SIM_DURATION
    cfg['scenario_properties']['steps']               = SIM_STEPS
    cfg['scenario_properties'].pop('indicator_variables', None)
    return cfg


def build_model(cfg):
    """Instantiate a fresh Model from a config dict."""
    p = cfg['scenario_properties']
    return Model(
        start_date          = p['start_date'],
        simulation_duration = p['simulation_duration'],
        steps               = p['steps'],
        min_altitude        = p['min_altitude'],
        max_altitude        = p['max_altitude'],
        n_shells            = p['n_shells'],
        launch_function     = p['launch_function'],
        integrator          = p['integrator'],
        density_model       = p['density_model'],
        LC                  = p['LC'],
        v_imp               = p.get('v_imp'),
        fragment_spreading  = p.get('fragment_spreading', False),
        parallel_processing = False,
        baseline            = p.get('baseline', False),
        launch_scenario     = p.get('launch_scenario'),
        SEP_mapping         = cfg.get('SEP_mapping'),
        indicator_variables = p.get('indicator_variables'),
    )


def run_simulation(cfg, launch_scale=1.0):
    """
    Run one simulation.  Returns (t, y, species_names, n_shells).
    If launch_scale != 1, the active-satellite FLM rates are scaled in-place
    after configure_species (before build_model).
    """
    model = build_model(cfg)
    model.configure_species(cfg['species'])

    if launch_scale != 1.0:
        _scale_launch_rates(model, launch_scale)

    model.run_model()
    sp = model.scenario_properties
    return (
        np.array(sp.output.t),
        np.array(sp.output.y),
        list(sp.species_names),
        sp.n_shells,
    )


def _scale_launch_rates(model, scale):
    """
    Scale the FLM launch arrays for active-satellite species (S*) by `scale`.
    Must be called after configure_species() but before run_model().
    """
    species_dict = model.scenario_properties.species
    all_species = []
    for group in species_dict.values():
        all_species.extend(group)

    for sp in all_species:
        if not sp.sym_name.startswith('S'):
            continue
        if not hasattr(sp, 'lambda_funs') or not sp.lambda_funs:
            continue
        scaled = []
        for lf in sp.lambda_funs:
            if isinstance(lf, np.ndarray):
                scaled.append(lf * scale)
            else:
                scaled.append(lf)   # 0 or None → unchanged
        sp.lambda_funs = scaled


def extract_metrics(t, y, species_names, n_shells):
    """
    From raw output arrays build time-series dicts and scalar summary metrics.
    """
    n_species = len(species_names)
    totals = {}
    for i, name in enumerate(species_names):
        totals[name] = np.sum(y[i * n_shells:(i + 1) * n_shells, :], axis=0)

    debris_names = [n for n in species_names if n.startswith('N')]
    sat_names    = [n for n in species_names if n.startswith('S')]

    total_debris = (
        np.sum([totals[n] for n in debris_names], axis=0)
        if debris_names else np.zeros_like(t)
    )
    total_sats = (
        np.sum([totals[n] for n in sat_names], axis=0)
        if sat_names else np.zeros_like(t)
    )

    # Net debris generation (proxy for cumulative collision activity)
    debris_generated = max(total_debris[-1] - total_debris[0], 0.0)

    return {
        't':              t,
        'total_debris':   total_debris,
        'total_sats':     total_sats,
        'species_totals': totals,
        # scalar summary
        'total_debris_final':  float(total_debris[-1]),
        'peak_debris_count':   float(np.max(total_debris)),
        'total_sats_final':    float(total_sats[-1]),
        'debris_generated':    float(debris_generated),
    }


# ── Per-parameter comparison plot ────────────────────────────────────────────
def plot_sweep(sweep_name, sweep_def, all_metrics, values):
    label    = sweep_def['label']
    filename = sweep_def['filename']
    n_vals   = len(values)
    colors   = [CMAP(i / (n_vals - 1)) for i in range(n_vals)]

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.suptitle(f'Sensitivity: {label}', fontsize=14, fontweight='bold')

    for (v, m), c in zip(zip(values, all_metrics), colors):
        lbl = f'{v:.3g}' if not sweep_def.get('is_launch_scale') else f'{v}×'
        t   = m['t']
        axes[0].plot(t, m['total_debris'],  color=c, label=lbl)
        axes[1].plot(t, m['total_sats'],    color=c, label=lbl)
        axes[2].plot(t, m['total_debris'] + m['total_sats'], color=c, label=lbl)

    for ax, title, ylabel in zip(
        axes,
        ['Total debris over time', 'Active satellites over time', 'Total objects over time'],
        ['Object count', 'Satellite count', 'Object count'],
    ):
        ax.set_xlabel('Year (simulation time)')
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.legend(title=label, fontsize=8)
        ax.grid(True, alpha=0.3)

    fig.tight_layout()
    path = os.path.join(FIGURES_DIR, f'{filename}.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  Saved → {path}')


# ── Final-value bar chart for a single sweep ─────────────────────────────────
def plot_sweep_bars(sweep_name, sweep_def, all_metrics, values):
    label    = sweep_def['label']
    filename = sweep_def['filename']
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle(f'Sensitivity: {label} — final state', fontsize=13, fontweight='bold')

    xlabels = [f'{v:.3g}' if not sweep_def.get('is_launch_scale') else f'{v}×' for v in values]
    debris_final = [m['total_debris_final'] for m in all_metrics]
    peak_debris  = [m['peak_debris_count']  for m in all_metrics]

    n   = len(values)
    clr = [CMAP(i / (n - 1)) for i in range(n)]

    for ax, vals, title in zip(
        axes,
        [debris_final, peak_debris],
        ['Debris at end of simulation', 'Peak debris count'],
    ):
        bars = ax.bar(xlabels, vals, color=clr, edgecolor='k', linewidth=0.5)
        ax.set_xlabel(label)
        ax.set_ylabel('Object count')
        ax.set_title(title)
        ax.grid(True, axis='y', alpha=0.3)
        for bar, val in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() * 1.01,
                    f'{val:,.0f}', ha='center', va='bottom', fontsize=8)

    fig.tight_layout()
    path = os.path.join(FIGURES_DIR, f'{filename}_bars.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  Saved → {path}')


# ── Run one complete sweep ────────────────────────────────────────────────────
def run_sweep(sweep_name, sweep_def, base_cfg):
    values      = sweep_def['values']
    param       = sweep_def.get('param')
    target_sp   = sweep_def.get('species', 'S')
    extra       = sweep_def.get('extra_params', {})
    is_launch   = sweep_def.get('is_launch_scale', False)

    print(f'\n{"="*60}')
    print(f'  Sweep: {sweep_def["label"]}')
    print(f'  Values: {values}')
    print(f'{"="*60}')

    all_metrics = []
    rows        = []

    for val in values:
        t0  = time.time()
        cfg = copy.deepcopy(base_cfg)

        if is_launch:
            launch_scale = val
        else:
            launch_scale = 1.0
            # patch the target species
            for sp in cfg['species']:
                if sp['sym_name'] == target_sp:
                    sp[param] = val
                    sp.update(extra)

        print(f'\n  Running {sweep_def["label"]} = {val} ...')
        try:
            t, y, snames, n_shells = run_simulation(cfg, launch_scale=launch_scale)
            m = extract_metrics(t, y, snames, n_shells)
            all_metrics.append(m)

            elapsed = time.time() - t0
            print(f'    Done in {elapsed:.1f}s | '
                  f'final debris={m["total_debris_final"]:,.0f} | '
                  f'peak debris={m["peak_debris_count"]:,.0f}')

            rows.append({
                'parameter': sweep_name,
                'value':     val,
                'total_debris_final': m['total_debris_final'],
                'peak_debris_count':  m['peak_debris_count'],
                'total_collisions':   m['debris_generated'],  # proxy
                'total_sats_final':   m['total_sats_final'],
            })

        except Exception as e:
            print(f'    ERROR: {e}')
            all_metrics.append(None)
            rows.append({
                'parameter': sweep_name, 'value': val,
                'total_debris_final': np.nan, 'peak_debris_count': np.nan,
                'total_collisions': np.nan, 'total_sats_final': np.nan,
            })

    # Filter out failed runs for plotting
    good = [(v, m) for v, m in zip(values, all_metrics) if m is not None]
    if good:
        good_vals, good_metrics = zip(*good)
        plot_sweep(sweep_name, sweep_def, good_metrics, good_vals)
        plot_sweep_bars(sweep_name, sweep_def, good_metrics, good_vals)

    return rows


# ── Tornado chart ─────────────────────────────────────────────────────────────
def plot_tornado(summary_df):
    """
    For each parameter: show range of total_debris_final (min to max).
    Sorted by range descending.
    """
    params = summary_df['parameter'].unique()
    records = []
    for p in params:
        sub   = summary_df[summary_df['parameter'] == p].dropna(subset=['total_debris_final'])
        if sub.empty:
            continue
        lo    = sub['total_debris_final'].min()
        hi    = sub['total_debris_final'].max()
        pivot = sub.loc[sub['total_debris_final'].sub(sub['total_debris_final'].median()).abs().idxmin(),
                        'total_debris_final']
        records.append({'param': p, 'lo': lo, 'hi': hi, 'range': hi - lo, 'mid': pivot})

    df = pd.DataFrame(records).sort_values('range', ascending=True)

    fig, ax = plt.subplots(figsize=(10, max(4, len(df) * 0.9)))

    # Map sweep key → nice label
    label_map = {s: SWEEPS[s]['label'] for s in SWEEPS}
    y_pos = np.arange(len(df))

    for i, row in enumerate(df.itertuples()):
        lbl = label_map.get(row.param, row.param)
        base = row.lo
        width = row.hi - row.lo
        color = CMAP(0.6 + 0.4 * i / max(len(df) - 1, 1))
        ax.barh(i, width, left=base, height=0.6, color=color, edgecolor='k', linewidth=0.5)
        ax.text(row.hi + width * 0.01, i, f'Δ={width:,.0f}', va='center', fontsize=9)
        ax.set_yticks(y_pos)
        ax.set_yticklabels([label_map.get(r.param, r.param) for r in df.itertuples()])

    ax.set_xlabel('Total debris at end of simulation')
    ax.set_title(f'Tornado chart: parameter sensitivity\n'
                 f'({SIM_DURATION}-year run, SEP2 launch scenario)',
                 fontsize=13, fontweight='bold')
    ax.grid(True, axis='x', alpha=0.3)
    fig.tight_layout()

    path = os.path.join(FIGURES_DIR, 'tornado_chart.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'\nTornado chart saved → {path}')


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('sweep', nargs='?', default=None,
                        choices=list(SWEEPS.keys()),
                        help='Which sweep to run (omit for all)')
    args = parser.parse_args()

    base_cfg = load_base_config()
    keys_to_run = [args.sweep] if args.sweep else list(SWEEPS.keys())

    all_rows  = []
    summary_csv = os.path.join(RESULTS_DIR, 'parameter_sensitivity_summary.csv')

    # Load existing CSV if present so we can append incrementally
    if os.path.exists(summary_csv):
        existing = pd.read_csv(summary_csv)
        existing_params = set(existing['parameter'].unique())
        # Pre-populate all_rows with existing data to avoid overwriting other sweeps
        all_rows = existing.to_dict('records')
    else:
        existing = pd.DataFrame()
        existing_params = set()

    for key in keys_to_run:
        if key in existing_params and args.sweep is None:
            print(f'\n  Skipping {key} (already in CSV — re-run with `python3 ... {key}` to redo)')
            continue
        # Remove stale rows for this parameter before adding fresh ones
        all_rows = [r for r in all_rows if r.get('parameter') != key]
        rows = run_sweep(key, SWEEPS[key], base_cfg)
        all_rows.extend(rows)

        # Save incrementally
        df_so_far = pd.DataFrame(all_rows)
        df_so_far.to_csv(summary_csv, index=False)
        print(f'  Summary CSV updated → {summary_csv}')

    # Reload full CSV (may include runs from previous sessions)
    full_df = pd.read_csv(summary_csv)
    print(f'\nFull summary:\n{full_df.to_string(index=False)}')

    if len(full_df['parameter'].unique()) >= 2:
        plot_tornado(full_df)
    else:
        print('\n(Tornado chart requires ≥2 parameters — run remaining sweeps first)')


if __name__ == '__main__':
    main()
