"""
Formal scenario campaign for governance robustness analysis.

16 governance configurations × 3 launch growths × 2 solar models × 2 behavioral responses
= 192 runs (100-year simulations each).

Checkpoints after each run; fully resumable.

Run from thesis-leo/ root:
    python3 exploration/03_formal_campaign.py [--start N] [--end N] [--only-plots]
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'pyssem-repo'))
sys.path.insert(0, os.path.dirname(__file__))

import json, copy, time, argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Patch

from sensitivity_sweep import (
    load_base_config, build_model, _scale_launch_rates, extract_metrics,
)

RESULTS_DIR  = 'results'
FIGURES_DIR  = 'figures/campaign'
CAMPAIGN_CSV = os.path.join(RESULTS_DIR, 'formal_campaign.csv')
SUMMARY_CSV  = os.path.join(RESULTS_DIR, 'campaign_summary.csv')

os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(FIGURES_DIR, exist_ok=True)

# ── Thresholds ────────────────────────────────────────────────────────────────
DEBRIS_CAPACITY_THRESHOLD = 30_000   # objects — ~1.7× baseline; defensible "yellow zone"
# Sustainability = debris slope over final 50 years ≤ 0

# ── Governance configurations ─────────────────────────────────────────────────
# All unspecified params inherit from baseline config (Pm=0.90, alpha=1e-5,
# slotting=1.0, deltat=8, launch_scale=1.0).
# 'pm' here is the TARGET Pm (responsive case); sluggish computed at runtime.

GOVERNANCE_CONFIGS = [
    # ── Category 1: Command & Control ──────────────────────────────────────────
    {'id': 'cnc_low',  'category': 'C&C',        'level': 'Low',
     'pm': 0.60, 'deltat': 25, 'alpha': 1e-5, 'slotting': 1.0, 'launch_scale': 1.0},
    {'id': 'cnc_med',  'category': 'C&C',        'level': 'Medium',
     'pm': 0.80, 'deltat': 12, 'alpha': 1e-5, 'slotting': 1.0, 'launch_scale': 1.0},
    {'id': 'cnc_high', 'category': 'C&C',        'level': 'High',
     'pm': 0.95, 'deltat':  5, 'alpha': 1e-5, 'slotting': 1.0, 'launch_scale': 1.0},

    # ── Category 2: Market-Based ───────────────────────────────────────────────
    {'id': 'mkt_low',  'category': 'Market',     'level': 'Low',
     'pm': 0.70, 'deltat':  8, 'alpha': 1e-5, 'slotting': 1.0, 'launch_scale': 1.00},
    {'id': 'mkt_med',  'category': 'Market',     'level': 'Medium',
     'pm': 0.85, 'deltat':  8, 'alpha': 1e-5, 'slotting': 1.0, 'launch_scale': 0.75},
    {'id': 'mkt_high', 'category': 'Market',     'level': 'High',
     'pm': 0.95, 'deltat':  8, 'alpha': 1e-5, 'slotting': 1.0, 'launch_scale': 0.50},

    # ── Category 3: Liability / Enforcement ───────────────────────────────────
    {'id': 'lib_low',  'category': 'Liability',  'level': 'Low',
     'pm': 0.65, 'deltat':  8, 'alpha': 1e-5, 'slotting': 1.0, 'launch_scale': 1.0},
    {'id': 'lib_med',  'category': 'Liability',  'level': 'Medium',
     'pm': 0.80, 'deltat':  8, 'alpha': 1e-5, 'slotting': 1.0, 'launch_scale': 1.0},
    {'id': 'lib_high', 'category': 'Liability',  'level': 'High',
     'pm': 0.95, 'deltat':  8, 'alpha': 1e-5, 'slotting': 1.0, 'launch_scale': 1.0},

    # ── Category 4: Coordination / STM ────────────────────────────────────────
    # Pm inherits baseline (0.90); sluggish applies the same 60% rule.
    {'id': 'stm_low',  'category': 'Coordination', 'level': 'Low',
     'pm': 0.90, 'deltat':  8, 'alpha': 1e-2, 'slotting': 0.0, 'launch_scale': 1.0},
    {'id': 'stm_med',  'category': 'Coordination', 'level': 'Medium',
     'pm': 0.90, 'deltat':  8, 'alpha': 1e-4, 'slotting': 0.5, 'launch_scale': 1.0},
    {'id': 'stm_high', 'category': 'Coordination', 'level': 'High',
     'pm': 0.90, 'deltat':  8, 'alpha': 1e-6, 'slotting': 1.0, 'launch_scale': 1.0},

    # ── Policy mixes ───────────────────────────────────────────────────────────
    {'id': 'mix_rules_stm', 'category': 'Mix',   'level': 'Rules+Coord',
     'pm': 0.85, 'deltat':  8, 'alpha': 1e-4, 'slotting': 0.5, 'launch_scale': 1.0},
    {'id': 'mix_fees_enf',  'category': 'Mix',   'level': 'Fees+Enforce',
     'pm': 0.90, 'deltat':  8, 'alpha': 1e-5, 'slotting': 1.0, 'launch_scale': 0.75},
    {'id': 'mix_all',       'category': 'Mix',   'level': 'All Four',
     'pm': 0.90, 'deltat':  8, 'alpha': 1e-4, 'slotting': 0.5, 'launch_scale': 0.75},

    # ── Governance failure ──────────────────────────────────────────────────────
    {'id': 'failure',       'category': 'Failure', 'level': 'Failure',
     'pm': 0.60, 'deltat':  8, 'alpha': 1e-5, 'slotting': 1.0, 'launch_scale': 2.0},
]

LAUNCH_GROWTHS       = [1.0, 2.0, 3.0]
SOLAR_MODELS         = ['static_exp_dens_func', 'JB2008_dens_func']
BEHAVIORAL_RESPONSES = ['responsive', 'sluggish']

BASELINE_PM = 0.60   # floor for sluggish calculation (no-governance compliance)


# ── Run configuration builder ─────────────────────────────────────────────────

def sluggish_pm(target_pm):
    """60% of improvement from governance floor realized."""
    return BASELINE_PM + 0.60 * (target_pm - BASELINE_PM)


def build_run_cfg(base_cfg, gov, launch_growth, solar, behavior):
    cfg = copy.deepcopy(base_cfg)

    # Effective launch scale: governance × uncertainty growth
    eff_launch = gov['launch_scale'] * launch_growth

    # Pm
    pm = gov['pm'] if behavior == 'responsive' else sluggish_pm(gov['pm'])

    # Patch species S
    for sp in cfg['species']:
        if sp['sym_name'] == 'S':
            sp['Pm']                    = pm
            sp['alpha']                 = gov['alpha']
            sp['alpha_active']          = gov['alpha']
            sp['deltat']                = gov['deltat']
            sp['slotted']               = True
            sp['slotting_effectiveness'] = gov['slotting']

    # Solar density model
    cfg['scenario_properties']['density_model'] = solar

    return cfg, eff_launch, pm


def build_run_id(gov_id, launch_growth, solar, behavior):
    solar_tag = 'jb' if 'JB2008' in solar else 'exp'
    return f"{gov_id}_g{launch_growth:.1f}_{solar_tag}_{behavior}"


# ── Metrics extraction ────────────────────────────────────────────────────────

def compute_metrics(t, y, snames, n_shells):
    m = extract_metrics(t, y, snames, n_shells)

    # Debris growth rate: slope of total debris over final 50 years
    total_debris = m['total_debris']
    mask = t >= 50
    if mask.sum() >= 2:
        slope, _ = np.polyfit(t[mask], total_debris[mask], 1)
    else:
        slope = (total_debris[-1] - total_debris[0]) / (t[-1] - t[0] + 1e-9)

    sustainable = bool(slope <= 0)
    capacity_ok  = bool(m['total_debris_final'] < DEBRIS_CAPACITY_THRESHOLD)
    col_per_sat  = (m['debris_generated'] / m['total_sats_final']
                    if m['total_sats_final'] > 1 else np.nan)

    return {
        **m,
        'debris_growth_rate': float(slope),
        'sustainable':        sustainable,
        'capacity_ok':        capacity_ok,
        'collision_risk_per_sat': float(col_per_sat) if not np.isnan(col_per_sat) else np.nan,
    }


# ── Simulation runner ─────────────────────────────────────────────────────────

def run_one(gov, launch_growth, solar, behavior, base_cfg):
    cfg, eff_launch, pm = build_run_cfg(base_cfg, gov, launch_growth, solar, behavior)
    p = cfg['scenario_properties']

    from pyssem.model import Model
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
    sp = model.scenario_properties
    t  = np.array(sp.output.t)
    y  = np.array(sp.output.y)
    return compute_metrics(t, y, list(sp.species_names), sp.n_shells)


# ── Campaign grid ──────────────────────────────────────────────────────────────

def build_grid():
    rows = []
    for gov in GOVERNANCE_CONFIGS:
        for lg in LAUNCH_GROWTHS:
            for solar in SOLAR_MODELS:
                for beh in BEHAVIORAL_RESPONSES:
                    run_id = build_run_id(gov['id'], lg, solar, beh)
                    rows.append({
                        'run_id':          run_id,
                        'gov_id':          gov['id'],
                        'category':        gov['category'],
                        'level':           gov['level'],
                        'launch_growth':   lg,
                        'solar':           'high' if 'JB2008' in solar else 'low',
                        'behavior':        beh,
                        'solar_model':     solar,
                        'target_pm':       gov['pm'],
                        'effective_pm':    gov['pm'] if beh == 'responsive' else sluggish_pm(gov['pm']),
                        'deltat':          gov['deltat'],
                        'alpha':           gov['alpha'],
                        'slotting':        gov['slotting'],
                        'gov_launch_scale': gov['launch_scale'],
                        'eff_launch_scale': gov['launch_scale'] * lg,
                    })
    return rows


# ── Main campaign runner ───────────────────────────────────────────────────────

def run_campaign(start_idx=0, end_idx=None):
    base_cfg = load_base_config()
    grid     = build_grid()
    total    = len(grid)
    if end_idx is None:
        end_idx = total

    # Load existing results to support resuming
    if os.path.exists(CAMPAIGN_CSV):
        existing = pd.read_csv(CAMPAIGN_CSV)
        done_ids = set(existing['run_id'])
        print(f'Resuming: {len(done_ids)}/{total} runs already complete.')
    else:
        existing = pd.DataFrame()
        done_ids = set()

    slice_ = grid[start_idx:end_idx]
    to_run = [r for r in slice_ if r['run_id'] not in done_ids]
    print(f'Slice [{start_idx}:{end_idx}]: {len(slice_)} runs, {len(to_run)} remaining.')

    session_rows = []
    t_start = time.time()

    for i, meta in enumerate(to_run, 1):
        t0 = time.time()
        gov = next(g for g in GOVERNANCE_CONFIGS if g['id'] == meta['gov_id'])
        solar = meta['solar_model']
        beh   = meta['behavior']
        lg    = meta['launch_growth']

        print(f'\n[{i}/{len(to_run)}] {meta["run_id"]}')
        print(f'  gov={meta["gov_id"]} | Pm={meta["effective_pm"]:.2f} | '
              f'launch={meta["eff_launch_scale"]:.2f}× | solar={meta["solar"]} | {beh}')

        try:
            m = run_one(gov, lg, solar, beh, base_cfg)
            elapsed = time.time() - t0

            row = {**meta,
                   'total_debris_final':      m['total_debris_final'],
                   'peak_debris_count':       m['peak_debris_count'],
                   'total_collisions':        m['debris_generated'],
                   'total_sats_final':        m['total_sats_final'],
                   'collision_risk_per_sat':  m['collision_risk_per_sat'],
                   'debris_growth_rate':      m['debris_growth_rate'],
                   'sustainable':             m['sustainable'],
                   'capacity_ok':             m['capacity_ok'],
                   'run_seconds':             elapsed,
                   'status':                  'ok'}

            print(f'  ✓ {elapsed:.0f}s | debris={m["total_debris_final"]:,.0f} | '
                  f'slope={m["debris_growth_rate"]:.1f}/yr | '
                  f'sustainable={m["sustainable"]} capacity_ok={m["capacity_ok"]}')

        except Exception as e:
            elapsed = time.time() - t0
            print(f'  ✗ ERROR: {e}')
            row = {**meta,
                   'total_debris_final': np.nan, 'peak_debris_count': np.nan,
                   'total_collisions': np.nan, 'total_sats_final': np.nan,
                   'collision_risk_per_sat': np.nan, 'debris_growth_rate': np.nan,
                   'sustainable': False, 'capacity_ok': False,
                   'run_seconds': elapsed, 'status': f'error: {e}'}

        session_rows.append(row)

        # Checkpoint: append new row to CSV
        checkpoint_df = pd.DataFrame([row])
        if os.path.exists(CAMPAIGN_CSV):
            checkpoint_df.to_csv(CAMPAIGN_CSV, mode='a', header=False, index=False)
        else:
            checkpoint_df.to_csv(CAMPAIGN_CSV, index=False)

        # Progress report
        elapsed_total = time.time() - t_start
        rate = i / elapsed_total
        remaining = (len(to_run) - i) / rate if rate > 0 else 0
        print(f'  Progress: {i}/{len(to_run)} | '
              f'elapsed={elapsed_total/3600:.2f}h | ETA={remaining/3600:.2f}h')

    print(f'\nCampaign slice done. {len(session_rows)} runs completed this session.')
    return session_rows


# ── Summary statistics ────────────────────────────────────────────────────────

def build_summary():
    df = pd.read_csv(CAMPAIGN_CSV)
    df = df[df['status'] == 'ok']

    rows = []
    for gov_id in df['gov_id'].unique():
        g = df[df['gov_id'] == gov_id]
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
            'pct_both_ok':     ((g['sustainable'] & g['capacity_ok']).mean() * 100),
        })

    summary = pd.DataFrame(rows)
    summary.to_csv(SUMMARY_CSV, index=False)
    print(f'Summary saved → {SUMMARY_CSV}')
    return summary


# ── Figures ───────────────────────────────────────────────────────────────────

GOV_ORDER = [g['id'] for g in GOVERNANCE_CONFIGS]
GOV_LABELS = {g['id']: f"{g['category']}\n{g['level']}" for g in GOVERNANCE_CONFIGS}
CAT_COLORS = {
    'C&C': '#2980b9', 'Market': '#27ae60',
    'Liability': '#8e44ad', 'Coordination': '#e67e22',
    'Mix': '#c0392b', 'Failure': '#7f8c8d',
}


def fig_heatmap(df):
    """Heatmap: gov_id × uncertainty cell → mean debris."""
    df = df[df['status'] == 'ok'].copy()

    # Create uncertainty label
    df['uncertainty'] = (df['solar'] + '☀ / ' + df['behavior'].str[:4]
                         + ' / ' + df['launch_growth'].astype(str) + '×')

    pivot = df.pivot_table(index='gov_id', columns='uncertainty',
                            values='total_debris_final', aggfunc='mean')
    pivot = pivot.reindex([g for g in GOV_ORDER if g in pivot.index])

    fig, ax = plt.subplots(figsize=(max(14, len(pivot.columns)*1.5), max(8, len(pivot)*0.6)))
    im = ax.imshow(pivot.values, cmap='RdYlGn_r', aspect='auto',
                   norm=mcolors.LogNorm(vmin=5000, vmax=120000))
    plt.colorbar(im, ax=ax, label='Total debris at year 100 (log scale)')

    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns, rotation=45, ha='right', fontsize=7)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels([GOV_LABELS.get(g, g) for g in pivot.index], fontsize=8)

    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            v = pivot.values[i, j]
            if not np.isnan(v):
                ax.text(j, i, f'{v/1000:.0f}k', ha='center', va='center',
                        fontsize=6, color='black' if v < 40000 else 'white')

    ax.set_title('Formal Campaign: Debris outcomes (mean over uncertainty cells)\n'
                 'governance config × [solar / behavior / launch growth]',
                 fontsize=11, fontweight='bold')
    fig.tight_layout()
    path = os.path.join(FIGURES_DIR, 'heatmap_debris.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved {path}')


def fig_threshold_bars(summary):
    """Bar chart: % scenarios passing sustainability + capacity per gov config."""
    summary = summary.reindex(summary.index[
        summary['gov_id'].isin([g['id'] for g in GOVERNANCE_CONFIGS])
    ] if 'gov_id' in summary.columns else summary.index)

    if 'gov_id' not in summary.columns:
        return

    summary = summary.set_index('gov_id').reindex(
        [g for g in GOV_ORDER if g in summary.index])

    labels = [GOV_LABELS.get(g, g) for g in summary.index]
    x = np.arange(len(labels))
    w = 0.25

    fig, ax = plt.subplots(figsize=(16, 6))
    ax.bar(x - w, summary['pct_sustainable'], w, label='Sustainable (slope≤0)', color='#27ae60', alpha=0.85)
    ax.bar(x,     summary['pct_capacity_ok'], w, label=f'Capacity OK (<{DEBRIS_CAPACITY_THRESHOLD/1000:.0f}k debris)', color='#2980b9', alpha=0.85)
    ax.bar(x + w, summary['pct_both_ok'],    w, label='Both OK',              color='#8e44ad', alpha=0.85)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
    ax.set_ylabel('% of uncertainty scenarios passing threshold')
    ax.set_ylim(0, 105)
    ax.axhline(100, color='gray', linestyle='--', linewidth=0.8)
    ax.legend(fontsize=9)
    ax.set_title('Governance robustness: threshold passage rates across 12 uncertainty scenarios',
                 fontsize=11, fontweight='bold')
    ax.grid(True, axis='y', alpha=0.3)

    fig.tight_layout()
    path = os.path.join(FIGURES_DIR, 'threshold_passage.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved {path}')


def fig_vulnerability_map(df):
    """Which gov configs fail under which uncertainty conditions."""
    df = df[df['status'] == 'ok'].copy()
    df['failed'] = ~(df['sustainable'] & df['capacity_ok'])

    # For each gov config: failure rate by uncertainty dimension
    gov_ids = [g for g in GOV_ORDER if g in df['gov_id'].unique()]

    rows = []
    for gid in gov_ids:
        g = df[df['gov_id'] == gid]
        gov = next(x for x in GOVERNANCE_CONFIGS if x['id'] == gid)
        for dim, vals in [('launch_growth', [1.0, 2.0, 3.0]),
                           ('solar', ['low', 'high']),
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

    fig, ax = plt.subplots(figsize=(14, max(8, len(pivot)*0.55)))
    im = ax.imshow(pivot.values, cmap='Reds', aspect='auto', vmin=0, vmax=100)
    plt.colorbar(im, ax=ax, label='% scenarios failing both thresholds')

    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns, rotation=40, ha='right', fontsize=8)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels([GOV_LABELS.get(g, g) for g in pivot.index], fontsize=8)

    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            v = pivot.values[i, j]
            if not np.isnan(v):
                ax.text(j, i, f'{v:.0f}%', ha='center', va='center',
                        fontsize=7, color='white' if v > 50 else 'black')

    ax.set_title('Vulnerability map: failure rate by uncertainty dimension',
                 fontsize=11, fontweight='bold')
    fig.tight_layout()
    path = os.path.join(FIGURES_DIR, 'vulnerability_map.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved {path}')


def fig_selected_trajectories(df_full, base_cfg):
    """
    Debris trajectories for 4 selected configs:
    baseline (cnc_med), best (mkt_high or cnc_high), worst (failure, 3×), mix_all.
    Uses the responsive + low-solar + 1× growth cell for each.
    """
    selected = [
        ('cnc_med',   1.0, 'static_exp_dens_func', 'responsive', 'C&C Medium (baseline-ish)', '#555555'),
        ('cnc_high',  1.0, 'static_exp_dens_func', 'responsive', 'C&C High',                  '#2980b9'),
        ('mix_all',   1.0, 'static_exp_dens_func', 'responsive', 'All-four mix',               '#27ae60'),
        ('failure',   3.0, 'static_exp_dens_func', 'sluggish',   'Governance failure (worst)', '#e74c3c'),
    ]

    fig, ax = plt.subplots(figsize=(10, 6))

    for gov_id, lg, solar, beh, label, color in selected:
        gov = next((g for g in GOVERNANCE_CONFIGS if g['id'] == gov_id), None)
        if gov is None:
            continue
        run_id = build_run_id(gov_id, lg, solar, beh)
        row = df_full[df_full['run_id'] == run_id]
        if row.empty:
            print(f'  Trajectory not in campaign data: {run_id} — re-running...')
            try:
                cfg, eff_launch, pm = build_run_cfg(base_cfg, gov, lg, solar, beh)
                p = cfg['scenario_properties']
                from pyssem.model import Model
                model = Model(
                    start_date=p['start_date'], simulation_duration=p['simulation_duration'],
                    steps=p['steps'], min_altitude=p['min_altitude'], max_altitude=p['max_altitude'],
                    n_shells=p['n_shells'], launch_function=p['launch_function'],
                    integrator=p['integrator'], density_model=p['density_model'],
                    LC=p['LC'], v_imp=p.get('v_imp'),
                    fragment_spreading=p.get('fragment_spreading', False),
                    parallel_processing=False, baseline=p.get('baseline', False),
                    launch_scenario=p.get('launch_scenario'), SEP_mapping=cfg.get('SEP_mapping'),
                    indicator_variables=None,
                )
                model.configure_species(cfg['species'])
                if eff_launch != 1.0:
                    _scale_launch_rates(model, eff_launch)
                model.run_model()
                sp = model.scenario_properties
                t_arr = np.array(sp.output.t)
                y_arr = np.array(sp.output.y)
                snames = list(sp.species_names)
                n_shells = sp.n_shells
                n_sp = len(snames)
                debris_ts = sum(
                    np.sum(y_arr[i * n_shells:(i + 1) * n_shells, :], axis=0)
                    for i, nm in enumerate(snames) if nm.startswith('N')
                )
                ax.plot(t_arr, debris_ts, color=color, linewidth=2.2, label=label)
            except Exception as e:
                print(f'  Error re-running {run_id}: {e}')
        else:
            # Can't re-derive time series from CSV — just mark final point
            final = row.iloc[0]['total_debris_final']
            ax.scatter([100], [final], color=color, s=80, zorder=5, label=f'{label} (final only)')

    ax.set_xlabel('Year (simulation time)', fontsize=11)
    ax.set_ylabel('Total debris objects', fontsize=11)
    ax.set_title('Debris trajectories: selected governance scenarios\n(responsive, low solar, 1× growth unless noted)',
                 fontsize=11, fontweight='bold')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:,.0f}'))

    fig.tight_layout()
    path = os.path.join(FIGURES_DIR, 'selected_trajectories.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved {path}')


def generate_all_figures():
    if not os.path.exists(CAMPAIGN_CSV):
        print('No campaign CSV found — run the campaign first.')
        return

    df   = pd.read_csv(CAMPAIGN_CSV)
    base = load_base_config()
    print(f'Loaded {len(df)} runs ({df["status"].value_counts().to_dict()})')

    fig_heatmap(df)
    summary = build_summary()
    fig_threshold_bars(summary)
    fig_vulnerability_map(df)
    fig_selected_trajectories(df, base)
    print('\nAll figures saved to figures/campaign/')


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--start',     type=int, default=0,   help='Start index in run grid')
    parser.add_argument('--end',       type=int, default=None, help='End index (exclusive)')
    parser.add_argument('--only-plots', action='store_true',  help='Skip runs, generate figures only')
    args = parser.parse_args()

    if args.only_plots:
        generate_all_figures()
    else:
        run_campaign(args.start, args.end)
        generate_all_figures()
