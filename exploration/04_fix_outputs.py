"""
Fix 1: Re-run 5 selected scenarios, save time series, plot trajectories.
Fix 2: Regenerate threshold bar chart with visible x-axis labels.
Fix 3: Low-solar-only summary CSV + heatmap + vulnerability map.

Run from thesis-leo/ root:
    python3 exploration/04_fix_outputs.py [--skip-runs]
"""

import sys, os, argparse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'pyssem-repo'))
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

from sensitivity_sweep import load_base_config, _scale_launch_rates
import importlib, sys
_camp = importlib.util.spec_from_file_location(
    "formal_campaign",
    os.path.join(os.path.dirname(__file__), "03_formal_campaign.py"))
_mod = importlib.util.module_from_spec(_camp)
_camp.loader.exec_module(_mod)
GOVERNANCE_CONFIGS      = _mod.GOVERNANCE_CONFIGS
FIGURES_DIR             = _mod.FIGURES_DIR
RESULTS_DIR             = _mod.RESULTS_DIR
build_run_cfg           = _mod.build_run_cfg
GOV_ORDER               = _mod.GOV_ORDER
GOV_LABELS              = _mod.GOV_LABELS
CAT_COLORS              = _mod.CAT_COLORS
DEBRIS_CAPACITY_THRESHOLD = _mod.DEBRIS_CAPACITY_THRESHOLD

os.makedirs(FIGURES_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# ── Scenario definitions for trajectory plot ──────────────────────────────────

TRAJECTORY_SCENARIOS = [
    {
        'run_id':      'cnc_med_g1.0_exp_responsive',
        'label':       'C&C Medium — baseline governance',
        'color':       '#7f8c8d',
        'linestyle':   '--',
        'gov_id':      'cnc_med',
        'launch_growth': 1.0,
        'solar':       'static_exp_dens_func',
        'behavior':    'responsive',
    },
    {
        'run_id':      'cnc_high_g1.0_exp_responsive',
        'label':       'C&C High — strong disposal rules',
        'color':       '#2980b9',
        'linestyle':   '-',
        'gov_id':      'cnc_high',
        'launch_growth': 1.0,
        'solar':       'static_exp_dens_func',
        'behavior':    'responsive',
    },
    {
        'run_id':      'mkt_high_g1.0_exp_responsive',
        'label':       'Market High — fees + disposal (most robust)',
        'color':       '#27ae60',
        'linestyle':   '-',
        'gov_id':      'mkt_high',
        'launch_growth': 1.0,
        'solar':       'static_exp_dens_func',
        'behavior':    'responsive',
    },
    {
        'run_id':      'cnc_high_g2.0_exp_sluggish',
        'label':       'C&C High + 2× growth + sluggish (vulnerability)',
        'color':       '#e67e22',
        'linestyle':   '-',
        'gov_id':      'cnc_high',
        'launch_growth': 2.0,
        'solar':       'static_exp_dens_func',
        'behavior':    'sluggish',
    },
    {
        'run_id':      'failure_g3.0_exp_sluggish',
        'label':       'Governance failure + 3× growth + sluggish (worst case)',
        'color':       '#e74c3c',
        'linestyle':   '-',
        'gov_id':      'failure',
        'launch_growth': 3.0,
        'solar':       'static_exp_dens_func',
        'behavior':    'sluggish',
    },
]


# ── Fix 1: trajectory time series ────────────────────────────────────────────

def run_trajectory_scenarios(base_cfg):
    from pyssem.model import Model

    ts_rows = []
    results  = {}

    for sc in TRAJECTORY_SCENARIOS:
        gov = next(g for g in GOVERNANCE_CONFIGS if g['id'] == sc['gov_id'])
        print(f'\n  Running: {sc["run_id"]} ...')

        cfg, eff_launch, pm = build_run_cfg(
            base_cfg, gov, sc['launch_growth'], sc['solar'], sc['behavior'])
        p = cfg['scenario_properties']

        model = Model(
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
            indicator_variables = None,
        )
        model.configure_species(cfg['species'])
        if eff_launch != 1.0:
            _scale_launch_rates(model, eff_launch)
        model.run_model()

        sp      = model.scenario_properties
        t_arr   = np.array(sp.output.t)
        y_arr   = np.array(sp.output.y)
        snames  = list(sp.species_names)
        n_shells = sp.n_shells

        debris_ts = np.zeros(len(t_arr))
        sats_ts   = np.zeros(len(t_arr))
        for i, nm in enumerate(snames):
            arr = np.sum(y_arr[i * n_shells:(i + 1) * n_shells, :], axis=0)
            if nm.startswith('N'):
                debris_ts += arr
            elif nm.startswith('S'):
                sats_ts += arr

        print(f'    final debris={debris_ts[-1]:,.0f}')

        for t_val, d_val, s_val in zip(t_arr, debris_ts, sats_ts):
            ts_rows.append({
                'run_id':       sc['run_id'],
                'label':        sc['label'],
                'year':         float(t_val),
                'total_debris': float(d_val),
                'total_sats':   float(s_val),
            })

        results[sc['run_id']] = {
            't': t_arr, 'debris': debris_ts, 'sats': sats_ts,
        }

    ts_df = pd.DataFrame(ts_rows)
    ts_csv = os.path.join(RESULTS_DIR, 'trajectory_timeseries.csv')
    ts_df.to_csv(ts_csv, index=False)
    print(f'\nSaved {ts_csv}')
    return results


def load_or_run_trajectories(base_cfg, skip_runs=False):
    ts_csv = os.path.join(RESULTS_DIR, 'trajectory_timeseries.csv')
    if skip_runs and os.path.exists(ts_csv):
        print('Loading existing trajectory data...')
        ts_df   = pd.read_csv(ts_csv)
        results = {}
        for sc in TRAJECTORY_SCENARIOS:
            sub = ts_df[ts_df['run_id'] == sc['run_id']]
            if not sub.empty:
                results[sc['run_id']] = {
                    't':      sub['year'].values,
                    'debris': sub['total_debris'].values,
                    'sats':   sub['total_sats'].values,
                }
        return results
    return run_trajectory_scenarios(base_cfg)


def plot_trajectories(results):
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    for sc in TRAJECTORY_SCENARIOS:
        rid = sc['run_id']
        if rid not in results:
            continue
        r = results[rid]
        kw = dict(color=sc['color'], linestyle=sc['linestyle'],
                  linewidth=2.2, label=sc['label'])
        axes[0].plot(r['t'], r['debris'], **kw)
        axes[1].plot(r['t'], r['sats'],   **kw)

    for ax, title, ylabel in zip(
        axes,
        ['Total debris objects over time', 'Active satellites over time'],
        ['Debris objects', 'Active satellites'],
    ):
        ax.set_xlabel('Simulation year', fontsize=11)
        ax.set_ylabel(ylabel, fontsize=11)
        ax.set_title(title, fontsize=11, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:,.0f}'))

    axes[0].axhline(DEBRIS_CAPACITY_THRESHOLD, color='red', linestyle=':', linewidth=1.2,
                    alpha=0.7, label=f'Capacity threshold ({DEBRIS_CAPACITY_THRESHOLD/1000:.0f}k)')
    axes[0].legend(fontsize=8, loc='upper left')
    axes[1].legend(fontsize=8, loc='upper left')

    fig.suptitle('Selected governance scenarios — 100-year debris trajectories\n'
                 '(static atmosphere, low solar activity)',
                 fontsize=12, fontweight='bold')
    plt.tight_layout()
    out = os.path.join(FIGURES_DIR, 'selected_trajectories.png')
    fig.savefig(out, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved {out}')


# ── Fix 2: threshold bar chart with labels ────────────────────────────────────

def plot_threshold_bars_fixed(summary):
    summary = summary.copy()
    if 'gov_id' not in summary.columns:
        print('summary missing gov_id column')
        return
    summary = summary.set_index('gov_id')
    ordered = [g for g in GOV_ORDER if g in summary.index]
    summary = summary.loc[ordered]

    labels    = [GOV_LABELS.get(g, g) for g in summary.index]
    bar_colors = [CAT_COLORS.get(
        next((gc['category'] for gc in GOVERNANCE_CONFIGS if gc['id'] == g), ''), '#888')
        for g in summary.index]

    x = np.arange(len(labels))
    w = 0.25

    fig, ax = plt.subplots(figsize=(16, 7))

    ax.bar(x - w, summary['pct_sustainable'], w,
           label='Sustainable (slope≤0)',
           color=[matplotlib.colors.to_rgba(c, 0.6) for c in bar_colors],
           edgecolor='white')
    ax.bar(x,     summary['pct_capacity_ok'], w,
           label=f'Capacity OK (<{DEBRIS_CAPACITY_THRESHOLD//1000}k debris)',
           color=[matplotlib.colors.to_rgba(c, 0.85) for c in bar_colors],
           edgecolor='white')
    ax.bar(x + w, summary['pct_both_ok'],    w,
           label='Both OK',
           color=bar_colors,
           edgecolor='white')

    # Value labels on top of "both OK" bars
    for xi, val in zip(x + w, summary['pct_both_ok']):
        ax.text(xi, val + 1.5, f'{val:.0f}%', ha='center', va='bottom', fontsize=7.5)

    # Category colour legend patches
    from matplotlib.patches import Patch
    cat_patches = [Patch(color=c, label=cat) for cat, c in CAT_COLORS.items()]

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha='right', fontsize=9)
    ax.set_ylabel('% of uncertainty scenarios passing threshold', fontsize=11)
    ax.set_ylim(0, 112)
    ax.axhline(100, color='gray', linestyle='--', linewidth=0.8, alpha=0.6)
    ax.grid(True, axis='y', alpha=0.3)

    # Two legend groups
    threshold_legend = ax.legend(fontsize=9, loc='upper left')
    ax.add_artist(threshold_legend)
    ax.legend(handles=cat_patches, title='Category', fontsize=8,
              loc='upper right', ncol=2)

    ax.set_title(
        'Governance robustness: threshold passage rates across 12 uncertainty scenarios\n'
        '(3 launch growths × 2 solar models × 2 behavioral responses)',
        fontsize=11, fontweight='bold')

    plt.tight_layout()
    out = os.path.join(FIGURES_DIR, 'threshold_passage.png')
    fig.savefig(out, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved {out}')


# ── Fix 3: low-solar-only analysis ────────────────────────────────────────────

def build_lowsolar_summary(df):
    df_low = df[(df['solar'] == 'low') & (df['status'] == 'ok')].copy()

    rows = []
    for gov_id in [g['id'] for g in GOVERNANCE_CONFIGS]:
        g = df_low[df_low['gov_id'] == gov_id]
        if g.empty:
            continue
        gov = next(x for x in GOVERNANCE_CONFIGS if x['id'] == gov_id)
        rows.append({
            'gov_id':          gov_id,
            'category':        gov['category'],
            'level':           gov['level'],
            'n_runs':          len(g),
            'debris_mean':     g['total_debris_final'].mean(),
            'debris_median':   g['total_debris_final'].median(),
            'debris_min':      g['total_debris_final'].min(),
            'debris_max':      g['total_debris_final'].max(),
            'pct_sustainable': g['sustainable'].mean() * 100,
            'pct_capacity_ok': g['capacity_ok'].mean() * 100,
            'pct_both_ok':     (g['sustainable'] & g['capacity_ok']).mean() * 100,
        })

    summary = pd.DataFrame(rows)
    out = os.path.join(RESULTS_DIR, 'campaign_summary_lowsolar.csv')
    summary.to_csv(out, index=False)
    print(f'Saved {out}')
    return summary, df_low


def fig_heatmap_lowsolar(df_low):
    df_low = df_low.copy()
    df_low['uncertainty'] = (
        df_low['behavior'].str[:4] + ' / '
        + df_low['launch_growth'].astype(str) + '×'
    )

    pivot = df_low.pivot_table(
        index='gov_id', columns='uncertainty',
        values='total_debris_final', aggfunc='mean')
    pivot = pivot.reindex([g for g in GOV_ORDER if g in pivot.index])

    fig, ax = plt.subplots(figsize=(10, max(8, len(pivot) * 0.6)))
    vmax = max(pivot.values[~np.isnan(pivot.values)].max(), 1)
    im = ax.imshow(pivot.values, cmap='RdYlGn_r', aspect='auto',
                   norm=mcolors.LogNorm(vmin=5000, vmax=max(vmax, 5001)))
    plt.colorbar(im, ax=ax, label='Total debris at year 100 (log scale)')

    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns, rotation=35, ha='right', fontsize=9)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels([GOV_LABELS.get(g, g) for g in pivot.index], fontsize=9)

    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            v = pivot.values[i, j]
            if not np.isnan(v):
                ax.text(j, i, f'{v/1000:.0f}k', ha='center', va='center',
                        fontsize=8, color='black' if v < 40000 else 'white')

    ax.set_title('Debris outcomes — LOW SOLAR only (static_exp)\n'
                 'governance config × [behavior / launch growth]',
                 fontsize=11, fontweight='bold')
    plt.tight_layout()
    out = os.path.join(FIGURES_DIR, 'heatmap_debris_lowsolar.png')
    fig.savefig(out, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved {out}')


def fig_vulnerability_lowsolar(df_low):
    df_low = df_low.copy()
    df_low['failed'] = ~(df_low['sustainable'] & df_low['capacity_ok'])

    gov_ids = [g['id'] for g in GOVERNANCE_CONFIGS if g['id'] in df_low['gov_id'].unique()]
    rows = []
    for gid in gov_ids:
        g = df_low[df_low['gov_id'] == gid]
        gov = next(x for x in GOVERNANCE_CONFIGS if x['id'] == gid)
        for dim, vals in [('launch_growth', [1.0, 2.0, 3.0]),
                           ('behavior', ['responsive', 'sluggish'])]:
            for val in vals:
                sub = g[g[dim] == val]
                if len(sub):
                    rows.append({
                        'gov_id': gid, 'category': gov['category'],
                        'dimension': f'{dim}={val}',
                        'failure_rate': sub['failed'].mean() * 100,
                    })

    vdf = pd.DataFrame(rows)
    pivot = vdf.pivot_table(index='gov_id', columns='dimension',
                             values='failure_rate', aggfunc='mean')
    pivot = pivot.reindex([g for g in GOV_ORDER if g in pivot.index])

    fig, ax = plt.subplots(figsize=(10, max(8, len(pivot) * 0.55)))
    im = ax.imshow(pivot.values, cmap='Reds', aspect='auto', vmin=0, vmax=100)
    plt.colorbar(im, ax=ax, label='% scenarios failing both thresholds')

    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns, rotation=35, ha='right', fontsize=9)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels([GOV_LABELS.get(g, g) for g in pivot.index], fontsize=9)

    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            v = pivot.values[i, j]
            if not np.isnan(v):
                ax.text(j, i, f'{v:.0f}%', ha='center', va='center',
                        fontsize=8, color='white' if v > 50 else 'black')

    ax.set_title('Vulnerability map — LOW SOLAR only (static_exp)\n'
                 'failure rate by launch growth and behavioral response',
                 fontsize=11, fontweight='bold')
    plt.tight_layout()
    out = os.path.join(FIGURES_DIR, 'vulnerability_map_lowsolar.png')
    fig.savefig(out, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved {out}')


def fig_threshold_bars_lowsolar(summary_low):
    summary_low = summary_low.copy()
    summary_low = summary_low.set_index('gov_id')
    ordered     = [g for g in GOV_ORDER if g in summary_low.index]
    summary_low = summary_low.loc[ordered]

    labels = [GOV_LABELS.get(g, g) for g in summary_low.index]
    bar_colors = [CAT_COLORS.get(
        next((gc['category'] for gc in GOVERNANCE_CONFIGS if gc['id'] == g), ''), '#888')
        for g in summary_low.index]

    x = np.arange(len(labels))
    w = 0.25

    fig, ax = plt.subplots(figsize=(16, 7))
    ax.bar(x - w, summary_low['pct_sustainable'], w, label='Sustainable',
           color=[matplotlib.colors.to_rgba(c, 0.6) for c in bar_colors], edgecolor='white')
    ax.bar(x,     summary_low['pct_capacity_ok'], w, label=f'Capacity OK (<{DEBRIS_CAPACITY_THRESHOLD//1000}k)',
           color=[matplotlib.colors.to_rgba(c, 0.85) for c in bar_colors], edgecolor='white')
    ax.bar(x + w, summary_low['pct_both_ok'],    w, label='Both OK',
           color=bar_colors, edgecolor='white')

    for xi, val in zip(x + w, summary_low['pct_both_ok']):
        ax.text(xi, val + 1.5, f'{val:.0f}%', ha='center', va='bottom', fontsize=7.5)

    from matplotlib.patches import Patch
    cat_patches = [Patch(color=c, label=cat) for cat, c in CAT_COLORS.items()]
    threshold_legend = ax.legend(fontsize=9, loc='upper left')
    ax.add_artist(threshold_legend)
    ax.legend(handles=cat_patches, title='Category', fontsize=8, loc='upper right', ncol=2)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha='right', fontsize=9)
    ax.set_ylabel('% of 6 low-solar uncertainty scenarios passing threshold', fontsize=11)
    ax.set_ylim(0, 112)
    ax.axhline(100, color='gray', linestyle='--', linewidth=0.8, alpha=0.6)
    ax.grid(True, axis='y', alpha=0.3)
    ax.set_title(
        'Governance robustness — LOW SOLAR only\n'
        '(3 launch growths × 2 behavioral responses, static atmosphere)',
        fontsize=11, fontweight='bold')

    plt.tight_layout()
    out = os.path.join(FIGURES_DIR, 'threshold_passage_lowsolar_grouped.png')
    fig.savefig(out, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved {out}')


def fig_robustness_ranking_lowsolar():
    """Clean horizontal robustness-ranking chart: one bar per governance
    config, sorted by share of low-solar uncertainty cells passing both
    thresholds (debris_median ascending as tiebreaker)."""
    CM_TO_IN = 1 / 2.54
    FIGW = 16 * CM_TO_IN

    plt.rcParams.update({
        'font.family':       'sans-serif',
        'font.sans-serif':   ['Helvetica', 'Arial', 'DejaVu Sans'],
        'font.size':         9,
        'axes.edgecolor':    '#444444',
        'axes.labelcolor':   '#222222',
        'axes.titlesize':    10.5,
        'axes.titleweight':  'bold',
        'axes.spines.top':   False,
        'axes.spines.right': False,
        'xtick.color':       '#444444',
        'ytick.color':       '#444444',
        'figure.facecolor':  'white',
        'axes.facecolor':    'white',
        'savefig.facecolor': 'white',
        'grid.color':        '#dddddd',
        'grid.linewidth':    0.6,
    })

    cat_colors = {
        'C&C':          '#5b7fb5',
        'Market':       '#4a8c5f',
        'Liability':    '#8a6db5',
        'Coordination': '#d68a3c',
        'Mix':          '#4aa3a3',
        'Failure':      '#b3503f',
    }

    summary_low = pd.read_csv(os.path.join(RESULTS_DIR, 'campaign_summary_lowsolar.csv'))
    summary_low = summary_low.sort_values(
        ['pct_both_ok', 'debris_median'], ascending=[False, True]).reset_index(drop=True)

    def label_for(row):
        if row['category'] == 'Failure':
            return 'Governance Failure'
        return f"{row['category']} – {row['level']}"

    labels = [label_for(r) for _, r in summary_low.iterrows()]
    values = summary_low['pct_both_ok'].values
    colors = [cat_colors.get(c, '#999999') for c in summary_low['category']]

    fig, ax = plt.subplots(figsize=(FIGW, FIGW * 1.1))

    y = np.arange(len(labels))[::-1]
    ax.barh(y, values, color=colors, height=0.62, zorder=3)

    for yi, val in zip(y, values):
        ax.text(val + 1.5, yi, f'{val:.0f}%', va='center', ha='left',
                fontsize=8, color='#333333')

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8.5)
    ax.set_xlim(0, 108)
    ax.set_xlabel('Share of conservative-atmosphere cells passing both thresholds (%)')
    ax.set_title('Robustness ranking under conservative atmosphere')
    ax.grid(True, axis='x', alpha=0.5)
    ax.set_axisbelow(True)

    from matplotlib.patches import Patch
    cat_patches = [Patch(facecolor=c, label=cat) for cat, c in cat_colors.items()]
    ax.legend(handles=cat_patches, title='Category', fontsize=7.5, title_fontsize=8,
              loc='lower right', frameon=False, ncol=2)

    plt.tight_layout()
    out = os.path.join(FIGURES_DIR, 'threshold_passage_lowsolar.png')
    fig.savefig(out, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved {out}')
    return summary_low[['gov_id', 'category', 'level', 'pct_both_ok', 'debris_median']]


# ── Main ──────────────────────────────────────────────────────────────────────

import matplotlib

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--skip-runs', action='store_true',
                        help='Use cached trajectory CSV instead of re-running')
    args = parser.parse_args()

    base_cfg = load_base_config()
    df       = pd.read_csv(os.path.join(RESULTS_DIR, 'formal_campaign.csv'))
    summary  = pd.read_csv(os.path.join(RESULTS_DIR, 'campaign_summary.csv'))

    print('=' * 60)
    print('Fix 1: Trajectory time series')
    print('=' * 60)
    results = load_or_run_trajectories(base_cfg, skip_runs=args.skip_runs)
    plot_trajectories(results)

    print('\n' + '=' * 60)
    print('Fix 2: Threshold bar chart with labels')
    print('=' * 60)
    plot_threshold_bars_fixed(summary)

    print('\n' + '=' * 60)
    print('Fix 3: Low-solar-only analysis')
    print('=' * 60)
    summary_low, df_low = build_lowsolar_summary(df)

    print('\nLow-solar robustness ranking:')
    ranked = summary_low.sort_values('pct_both_ok', ascending=False)
    print(ranked[['gov_id', 'category', 'level', 'pct_both_ok', 'debris_median']].to_string(index=False))

    fig_heatmap_lowsolar(df_low)
    fig_vulnerability_lowsolar(df_low)
    fig_threshold_bars_lowsolar(summary_low)
    fig_robustness_ranking_lowsolar()

    print('\nAll fixes complete.')
