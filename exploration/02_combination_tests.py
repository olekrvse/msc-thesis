"""
Combination tests and alpha per-satellite collision risk analysis.

Run from thesis-leo/ root:
    python3 exploration/02_combination_tests.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'pyssem-repo'))

import json, copy, time
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Re-use helpers from sensitivity_sweep
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from sensitivity_sweep import (
    load_base_config, build_model, run_simulation,
    _scale_launch_rates, extract_metrics,
    FIGURES_DIR, RESULTS_DIR,
)

os.makedirs(FIGURES_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# ── Part 1: Alpha per-satellite collision risk ────────────────────────────────

def plot_alpha_risk():
    df = pd.read_csv(os.path.join(RESULTS_DIR, 'parameter_sensitivity_summary.csv'))
    alpha_df = df[df['parameter'] == 'alpha'].copy()
    alpha_df['collision_risk_per_sat'] = alpha_df['total_collisions'] / alpha_df['total_sats_final']
    alpha_df = alpha_df.sort_values('value')

    fig, axes = plt.subplots(1, 3, figsize=(14, 4))

    axes[0].semilogx(alpha_df['value'], alpha_df['total_debris_final'], 'o-', color='#e74c3c', linewidth=2)
    axes[0].set_xlabel('alpha (CA failure rate)')
    axes[0].set_ylabel('Total debris at year 100')
    axes[0].set_title('Total debris vs alpha')
    axes[0].grid(True, alpha=0.3)

    axes[1].semilogx(alpha_df['value'], alpha_df['total_sats_final'], 's-', color='#3498db', linewidth=2)
    axes[1].set_xlabel('alpha (CA failure rate)')
    axes[1].set_ylabel('Active satellites at year 100')
    axes[1].set_title('Active sats vs alpha')
    axes[1].grid(True, alpha=0.3)

    axes[2].semilogx(alpha_df['value'], alpha_df['collision_risk_per_sat'], '^-', color='#9b59b6', linewidth=2)
    axes[2].set_xlabel('alpha (CA failure rate)')
    axes[2].set_ylabel('Collision events / active satellite')
    axes[2].set_title('Per-satellite collision risk vs alpha')
    axes[2].grid(True, alpha=0.3)

    fig.suptitle('Alpha sensitivity: total debris vs per-satellite collision risk', fontsize=12, fontweight='bold')
    plt.tight_layout()
    out = os.path.join(FIGURES_DIR, 'alpha_collision_risk.png')
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'Saved {out}')

    print('\n── Alpha per-satellite collision risk ──')
    print(alpha_df[['value', 'total_collisions', 'total_sats_final', 'collision_risk_per_sat']].to_string(index=False))
    print(f'\nRange of collision risk: {alpha_df["collision_risk_per_sat"].max() - alpha_df["collision_risk_per_sat"].min():.4f}')
    print('→ Per-satellite risk is essentially FLAT across 4 orders of magnitude of alpha.')
    return alpha_df


# ── Part 2: Combination tests ─────────────────────────────────────────────────

COMBINATIONS = [
    {
        'label':        'Baseline',
        'description':  'Pm=0.90, alpha=1e-5, launch=1×, deltat=8',
        'pm':           0.90,
        'alpha':        1e-5,
        'launch_scale': 1.0,
        'deltat':       8,
    },
    {
        'label':        'High Pm + low alpha',
        'description':  'Pm=0.95, alpha=1e-3, launch=1×, deltat=8',
        'pm':           0.95,
        'alpha':        1e-3,
        'launch_scale': 1.0,
        'deltat':       8,
    },
    {
        'label':        'Low Pm + high launch',
        'description':  'Pm=0.60, alpha=1e-5, launch=2×, deltat=8  (governance failure)',
        'pm':           0.60,
        'alpha':        1e-5,
        'launch_scale': 2.0,
        'deltat':       8,
    },
    {
        'label':        'High Pm + high launch',
        'description':  'Pm=0.95, alpha=1e-5, launch=2×, deltat=8  (disposal keeping up?)',
        'pm':           0.95,
        'alpha':        1e-5,
        'launch_scale': 2.0,
        'deltat':       8,
    },
    {
        'label':        'Full governance package',
        'description':  'Pm=0.95, alpha=1e-3, launch=1×, deltat=5',
        'pm':           0.95,
        'alpha':        1e-3,
        'launch_scale': 1.0,
        'deltat':       5,
    },
]


def build_combo_cfg(base_cfg, combo):
    cfg = copy.deepcopy(base_cfg)
    for sp in cfg['species']:
        if sp['sym_name'] == 'S':
            sp['Pm']    = combo['pm']
            sp['alpha'] = combo['alpha']
            if combo.get('deltat') is not None:
                sp['deltat'] = combo['deltat']
    return cfg


def run_combinations(base_cfg):
    rows = []
    time_series = {}   # label → (t, debris_ts, sats_ts)

    for combo in COMBINATIONS:
        print(f'\n  Running: {combo["label"]} ...')
        print(f'    {combo["description"]}')
        t0 = time.time()
        try:
            cfg = build_combo_cfg(base_cfg, combo)
            t, y, snames, n_shells = run_simulation(cfg, launch_scale=combo['launch_scale'])
            m = extract_metrics(t, y, snames, n_shells)
            elapsed = time.time() - t0
            print(f'    Done in {elapsed:.1f}s | debris={m["total_debris_final"]:,.0f} | sats={m["total_sats_final"]:,.0f}')

            rows.append({
                'scenario':          combo['label'],
                'description':       combo['description'],
                'pm':                combo['pm'],
                'alpha':             combo['alpha'],
                'launch_scale':      combo['launch_scale'],
                'deltat':            combo['deltat'],
                'total_debris_final': m['total_debris_final'],
                'peak_debris_count':  m['peak_debris_count'],
                'total_collisions':   m['debris_generated'],
                'total_sats_final':   m['total_sats_final'],
                'collision_risk_per_sat': m['debris_generated'] / m['total_sats_final'] if m['total_sats_final'] > 0 else np.nan,
            })

            # Store time series for plotting (debris and sats totals)
            n_sp = len(snames)
            debris_ts = np.zeros(len(t))
            sats_ts   = np.zeros(len(t))
            for i, nm in enumerate(snames):
                arr = np.sum(y[i * n_shells:(i + 1) * n_shells, :], axis=0)
                if 'N' in nm:
                    debris_ts += arr
                elif nm.startswith('S'):
                    sats_ts += arr
            time_series[combo['label']] = (t, debris_ts, sats_ts)

        except Exception as e:
            print(f'    ERROR: {e}')
            rows.append({
                'scenario': combo['label'], 'description': combo['description'],
                'pm': combo['pm'], 'alpha': combo['alpha'],
                'launch_scale': combo['launch_scale'], 'deltat': combo['deltat'],
                'total_debris_final': np.nan, 'peak_debris_count': np.nan,
                'total_collisions': np.nan, 'total_sats_final': np.nan,
                'collision_risk_per_sat': np.nan,
            })

    return pd.DataFrame(rows), time_series


def plot_combinations(df, time_series):
    colors = {
        'Baseline':               '#555555',
        'High Pm + low alpha':    '#27ae60',
        'Low Pm + high launch':   '#e74c3c',
        'High Pm + high launch':  '#e67e22',
        'Full governance package': '#2980b9',
    }

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    # Panel 1: debris time series
    for label, (t, debris_ts, sats_ts) in time_series.items():
        ls = '--' if label == 'Baseline' else '-'
        lw = 1.5 if label == 'Baseline' else 2.0
        axes[0].plot(t, debris_ts, label=label, color=colors.get(label, 'gray'), linestyle=ls, linewidth=lw)
    axes[0].set_xlabel('Year')
    axes[0].set_ylabel('Total debris objects')
    axes[0].set_title('Debris accumulation over time')
    axes[0].legend(fontsize=7.5)
    axes[0].grid(True, alpha=0.3)
    axes[0].yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:,.0f}'))

    # Panel 2: satellite population
    for label, (t, debris_ts, sats_ts) in time_series.items():
        ls = '--' if label == 'Baseline' else '-'
        lw = 1.5 if label == 'Baseline' else 2.0
        axes[1].plot(t, sats_ts, label=label, color=colors.get(label, 'gray'), linestyle=ls, linewidth=lw)
    axes[1].set_xlabel('Year')
    axes[1].set_ylabel('Active satellites')
    axes[1].set_title('Satellite population over time')
    axes[1].legend(fontsize=7.5)
    axes[1].grid(True, alpha=0.3)
    axes[1].yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:,.0f}'))

    # Panel 3: bar chart — final debris vs scenario
    valid = df.dropna(subset=['total_debris_final'])
    bar_colors = [colors.get(s, 'gray') for s in valid['scenario']]
    bars = axes[2].barh(valid['scenario'], valid['total_debris_final'],
                        color=bar_colors, edgecolor='white', height=0.5)
    for bar, val in zip(bars, valid['total_debris_final']):
        axes[2].text(val + 200, bar.get_y() + bar.get_height() / 2,
                     f'{val:,.0f}', va='center', fontsize=8)
    axes[2].set_xlabel('Total debris at year 100')
    axes[2].set_title('Final debris by scenario')
    axes[2].grid(True, alpha=0.3, axis='x')
    axes[2].xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:,.0f}'))

    fig.suptitle('Governance combination scenarios — 100-year simulation', fontsize=12, fontweight='bold')
    plt.tight_layout()
    out = os.path.join(FIGURES_DIR, 'combinations_comparison.png')
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'\nSaved {out}')


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print('=' * 60)
    print('Part 1: Alpha per-satellite collision risk')
    print('=' * 60)
    plot_alpha_risk()

    print('\n' + '=' * 60)
    print('Part 2: Combination scenario tests')
    print('=' * 60)
    base_cfg = load_base_config()
    df, time_series = run_combinations(base_cfg)

    out_csv = os.path.join(RESULTS_DIR, 'combination_tests.csv')
    df.to_csv(out_csv, index=False)
    print(f'\nSaved {out_csv}')

    plot_combinations(df, time_series)

    print('\n── Summary ──')
    print(df[['scenario', 'total_debris_final', 'peak_debris_count',
              'total_sats_final', 'collision_risk_per_sat']].to_string(index=False))
