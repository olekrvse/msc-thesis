"""
Generate four thesis figures with a consistent professional style:
white background, sans-serif, muted colors, 300dpi, ~16cm wide.

Fig 5.1 — Pm sweep (7x range)
Fig 5.2 — Market High vs Governance Failure trajectories
Fig 5.4 — Behavioral fault line (grouped bar)
Fig 4.2 — Campaign design schematic (diagram)

Run from thesis-leo/ root:
    python3 exploration/05_thesis_figures_ch5.py
"""

import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'figures', 'thesis')
os.makedirs(OUT_DIR, exist_ok=True)

CM_TO_IN = 1 / 2.54
FIGW = 16 * CM_TO_IN   # ~6.30 in

# ── Shared style ───────────────────────────────────────────────────────────
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

C_GREEN  = '#4a8c5f'   # market high / pass
C_RED    = '#b3503f'   # failure / fail
C_BLUE   = '#5b7fb5'   # responsive
C_ORANGE = '#d68a3c'   # sluggish
C_GRAY   = '#999999'   # threshold lines
C_DARK   = '#333333'


# ─────────────────────────────────────────────────────────────────────────────
# Figure 5.1 — Pm sweep
# ─────────────────────────────────────────────────────────────────────────────

def fig_5_1():
    ps = pd.read_csv('results/parameter_sensitivity_summary.csv')
    pm = ps[ps['parameter'] == 'pm'].sort_values('value')
    x = pm['value'].values
    y = pm['total_debris_final'].values

    fig, ax = plt.subplots(figsize=(FIGW, FIGW * 0.68))

    ax.plot(x, y, '-o', color=C_BLUE, linewidth=2, markersize=5.5,
            markerfacecolor='white', markeredgewidth=1.5, zorder=3)

    # Capacity threshold
    ax.axhline(30000, color=C_GRAY, linestyle='--', linewidth=1.1, zorder=1)
    ax.text(0.985, 31200, 'Capacity threshold (30,000)', ha='right', va='bottom',
            fontsize=7.5, color=C_GRAY)

    # Endpoint annotations
    ax.annotate(f'{y[0]:,.0f}',
                 xy=(x[0], y[0]), xytext=(x[0] + 0.012, y[0] + 1800),
                 fontsize=8.5, fontweight='bold', color=C_DARK)
    ax.annotate(f'{y[-1]:,.0f}',
                 xy=(x[-1], y[-1]), xytext=(x[-1], y[-1] - 2400),
                 fontsize=8.5, fontweight='bold', color=C_DARK,
                 ha='right', va='top')

    # 7x range bracket/annotation
    ax.annotate('', xy=(0.52, y[-1]), xytext=(0.52, y[0]),
                 arrowprops=dict(arrowstyle='<->', color=C_DARK, linewidth=1.0))
    ax.text(0.535, (y[0] + y[-1]) / 2, '7.1× range',
            fontsize=9, fontweight='bold', color=C_DARK, va='center',
            rotation=90)

    ax.set_xlabel('Post-mission disposal compliance, Pm')
    ax.set_ylabel('Total debris objects at year 100')
    ax.set_title('Disposal compliance dominates long-run debris accumulation')
    ax.set_xlim(0.47, 1.01)
    ax.set_ylim(0, 70000)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v:,.0f}'))
    ax.grid(True, axis='y', alpha=0.6)
    ax.set_axisbelow(True)

    plt.tight_layout()
    out = os.path.join(OUT_DIR, 'fig_5_1_pm_sweep.png')
    plt.savefig(out, dpi=300, bbox_inches='tight')
    plt.close()
    print(f'Saved {out}')


# ─────────────────────────────────────────────────────────────────────────────
# Figure 5.2 — Market High vs Governance Failure trajectories
# ─────────────────────────────────────────────────────────────────────────────

def fig_5_2():
    ts   = pd.read_csv('results/trajectory_timeseries.csv')
    camp = pd.read_csv('results/formal_campaign.csv')

    best_id = 'mkt_high_g1.0_exp_responsive'
    fail_id = 'failure_g3.0_exp_sluggish'

    best    = ts[ts['run_id'] == best_id].sort_values('year')
    failure = ts[ts['run_id'] == fail_id].sort_values('year')

    best_meta = camp[camp['run_id'] == best_id].iloc[0]
    fail_meta = camp[camp['run_id'] == fail_id].iloc[0]

    def fmt_label(name, meta):
        return (f"{name} — Pm={meta['effective_pm']:.2f}, "
                f"{meta['gov_launch_scale']:.2g}× launch, "
                f"{meta['launch_growth']:.0f}× growth, {meta['behavior']}")

    fig, ax = plt.subplots(figsize=(FIGW, FIGW * 0.62))

    ax.plot(best['year'], best['total_debris'], color=C_GREEN, linewidth=2.2,
            label=fmt_label('Market High', best_meta))
    ax.plot(failure['year'], failure['total_debris'], color=C_RED, linewidth=2.2,
            label=fmt_label('Governance Failure', fail_meta))

    ax.axhline(30000, color=C_GRAY, linestyle='--', linewidth=1.1, zorder=1)
    ax.text(50, 33500, 'Capacity threshold (30,000)', fontsize=7.5, color=C_GRAY,
            ha='center', va='bottom')

    # Terminal values computed for the verification summary only — not drawn on the figure
    best_final = best['total_debris'].iloc[-1]
    fail_final = failure['total_debris'].iloc[-1]

    ax.set_xlabel('Simulation year')
    ax.set_ylabel('Total debris objects')
    ax.set_title('Robust governance and policy failure diverge sharply')
    ax.set_xlim(0, 103)
    ax.set_xticks([0, 20, 40, 60, 80, 100])
    ax.set_ylim(0, max(fail_final, best_final) * 1.12)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v:,.0f}'))
    ax.grid(True, axis='y', alpha=0.6)
    ax.set_axisbelow(True)
    ax.legend(loc='upper left', fontsize=7.5, frameon=False)

    plt.tight_layout()
    out = os.path.join(OUT_DIR, 'fig_5_2_best_vs_worst.png')
    plt.savefig(out, dpi=300, bbox_inches='tight')
    plt.close()
    print(f'Saved {out}')

    return {
        'best_id': best_id, 'fail_id': fail_id,
        'best_final': best_final, 'fail_final': fail_final,
        'best_label': fmt_label('Market High', best_meta),
        'fail_label': fmt_label('Governance Failure', fail_meta),
        'out': out,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Figure 5.4 — Behavioral fault line
# ─────────────────────────────────────────────────────────────────────────────

def fig_5_4():
    df = pd.read_csv('results/formal_campaign.csv')
    sel = df[(df['solar'] == 'low') & (df['launch_growth'] == 2.0) &
             (df['gov_id'].isin(['cnc_high', 'mkt_high']))]

    groups = ['C&C High', 'Market High']
    gov_ids = ['cnc_high', 'mkt_high']

    resp_vals = []
    slug_vals = []
    for gid in gov_ids:
        row_r = sel[(sel['gov_id'] == gid) & (sel['behavior'] == 'responsive')]
        row_s = sel[(sel['gov_id'] == gid) & (sel['behavior'] == 'sluggish')]
        resp_vals.append(row_r['total_debris_final'].iloc[0])
        slug_vals.append(row_s['total_debris_final'].iloc[0])

    fig, ax = plt.subplots(figsize=(FIGW, FIGW * 0.68))

    x = range(len(groups))
    width = 0.32

    bars_r = ax.bar([i - width/2 for i in x], resp_vals, width,
                     color=C_BLUE, label='Responsive', zorder=3)
    bars_s = ax.bar([i + width/2 for i in x], slug_vals, width,
                     color=C_ORANGE, label='Sluggish response', zorder=3)

    for bar, val in zip(bars_r, resp_vals):
        ax.text(bar.get_x() + bar.get_width()/2, val + 800, f'{val:,.0f}',
                ha='center', va='bottom', fontsize=8.5, fontweight='bold', color=C_DARK)
    for bar, val in zip(bars_s, slug_vals):
        ax.text(bar.get_x() + bar.get_width()/2, val + 800, f'{val:,.0f}',
                ha='center', va='bottom', fontsize=8.5, fontweight='bold', color=C_DARK)

    ax.axhline(30000, color=C_GRAY, linestyle='--', linewidth=1.1, zorder=1)
    ax.text(-0.58, 31000, 'Capacity threshold (30,000)', fontsize=7.5, color=C_GRAY,
            ha='left', va='bottom')

    ax.set_xticks(list(x))
    ax.set_xticklabels(groups)
    ax.set_ylabel('Total debris objects at year 100')
    ax.set_title('Single-channel governance fails under behavioral sluggishness')
    ax.set_ylim(0, 56000)
    ax.set_xlim(-0.6, 1.6)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v:,.0f}'))
    ax.grid(True, axis='y', alpha=0.6)
    ax.set_axisbelow(True)
    ax.legend(loc='upper right', fontsize=8, frameon=False)

    plt.tight_layout()
    out = os.path.join(OUT_DIR, 'fig_5_4_behavioral_faultline.png')
    plt.savefig(out, dpi=300, bbox_inches='tight')
    plt.close()
    print(f'Saved {out}')

    return {
        'groups': groups, 'gov_ids': gov_ids,
        'resp_vals': resp_vals, 'slug_vals': slug_vals,
        'out': out,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Figure 4.2 — Campaign design schematic
# ─────────────────────────────────────────────────────────────────────────────

def fig_4_2():
    import textwrap

    XLIM, YLIM = 15.0, 8.5
    fig, ax = plt.subplots(figsize=(FIGW, FIGW * (YLIM / XLIM)))
    ax.set_xlim(0, XLIM)
    ax.set_ylim(0, YLIM)
    ax.axis('off')

    FIGH_IN = FIGW * (YLIM / XLIM)
    UNIT_PT_X = FIGW * 72 / XLIM
    UNIT_PT_Y = FIGH_IN * 72 / YLIM

    def wrapped_box(x, y_top, w, label, color, fontsize=8, txtcolor='white'):
        """Draw a box whose height auto-fits its (auto-wrapped) text. Returns box height."""
        chars_per_line = max(6, int((w * UNIT_PT_X - 10) / (fontsize * 0.5)))
        lines = []
        for part in label.split('\n'):
            wrapped = textwrap.wrap(part, chars_per_line)
            lines.extend(wrapped if wrapped else [''])
        line_h = (fontsize * 1.35) / UNIT_PT_Y
        h = len(lines) * line_h + 0.12
        rect = FancyBboxPatch((x, y_top - h), w, h, boxstyle='round,pad=0.045',
                               facecolor=color, edgecolor='none', zorder=3)
        ax.add_patch(rect)
        ax.text(x + w/2, y_top - h/2, '\n'.join(lines), ha='center', va='center',
                fontsize=fontsize, fontweight='bold', color=txtcolor, zorder=4,
                linespacing=1.3)
        return h

    def arrow(x0, y0, x1, y1, color='#888888', lw=1.3, style='->'):
        ax.annotate('', xy=(x1, y1), xytext=(x0, y0),
                     arrowprops=dict(arrowstyle=style, color=color, lw=lw),
                     zorder=2)

    # ── Category colors ─────────────────────────────────────────────────────
    cat_colors = {
        'C&C':          C_BLUE,
        'Market':       C_GREEN,
        'Liability':    '#8a6db5',
        'Coordination': C_ORANGE,
        'Mix':          '#4aa3a3',
        'Failure':      C_RED,
    }

    # ── Column 1: 16 governance configs grouped by category ──────────────────
    col1_x, col1_w = 0.3, 4.1
    header_y = 6.8
    ax.text(col1_x + col1_w/2, header_y, '16 Governance Configs',
            ha='center', fontsize=8.5, fontweight='bold', color='#222222')

    cat_rows = [
        ('Command & Control\n4 levels',      cat_colors['C&C']),
        ('Market-Based\n4 levels',           cat_colors['Market']),
        ('Liability / Enforcement\n4 levels', cat_colors['Liability']),
        ('Coordination / STM\n4 levels',     cat_colors['Coordination']),
        ('Policy Mixes\n3 configurations',   cat_colors['Mix']),
        ('Governance Failure\n1 configuration', cat_colors['Failure']),
    ]
    y_cursor = header_y - 0.45
    col1_top = y_cursor
    for label, color in cat_rows:
        h = wrapped_box(col1_x, y_cursor, col1_w, label, color, fontsize=8)
        y_cursor -= (h + 0.12)
    col1_bottom = y_cursor + 0.12
    center_y = (col1_top + col1_bottom) / 2

    # Bracket on right edge of column 1
    bracket_x = col1_x + col1_w + 0.12
    ax.plot([bracket_x, bracket_x], [col1_bottom, col1_top], color='#999999', lw=1.2, zorder=2)
    ax.plot([bracket_x - 0.08, bracket_x], [col1_top, col1_top], color='#999999', lw=1.2, zorder=2)
    ax.plot([bracket_x - 0.08, bracket_x], [col1_bottom, col1_bottom], color='#999999', lw=1.2, zorder=2)

    # ── Column 2: uncertainty dimensions × combination ────────────────────────
    col2_x, col2_w = 5.05, 3.4
    ax.text(col2_x + col2_w/2, header_y, 'Uncertainty Dimensions',
            ha='center', fontsize=8.5, fontweight='bold', color='#222222')

    uncertainty_rows = [
        ('Launch growth\n1× / 2× / 3×',            '#9a9a9a'),
        ('Atmosphere\nstatic / JB2008',            '#9a9a9a'),
        ('Behavioral response\nresponsive / sluggish', '#9a9a9a'),
    ]
    col2_top = center_y + 1.92
    y_cursor = col2_top
    centers2 = []
    for label, color in uncertainty_rows:
        h = wrapped_box(col2_x, y_cursor, col2_w, label, color, fontsize=8)
        centers2.append((y_cursor, h))
        y_cursor -= (h + 0.18)

    # small down-arrows linking the three uncertainty boxes
    for (yt, h), (yt2, h2) in zip(centers2[:-1], centers2[1:]):
        arrow(col2_x + col2_w/2, yt - h, col2_x + col2_w/2, yt2, color='#aaaaaa', lw=1.0)

    y_cursor -= 0.10
    h_combo = wrapped_box(col2_x, y_cursor, col2_w, '16 × 3 × 2 × 2\n= 192 runs', C_DARK, fontsize=10)
    combo_top, combo_h = y_cursor, h_combo
    combo_center_y = combo_top - combo_h / 2
    col2_bottom = combo_top - combo_h

    arrow(col2_x + col2_w/2, centers2[-1][0] - centers2[-1][1], col2_x + col2_w/2, combo_top, color='#aaaaaa', lw=1.0)

    # Arrow column1 -> column2 (from bracket midpoint into the uncertainty stack)
    arrow(bracket_x, center_y, col2_x - 0.05, center_y, color='#888888', lw=1.4)

    # ── Column 3: evaluation thresholds ───────────────────────────────────────
    col3_x, col3_w = 9.25, 3.6
    ax.text(col3_x + col3_w/2, header_y, 'Evaluation (per run)',
            ha='center', fontsize=8.5, fontweight='bold', color='#222222')

    threshold_rows = [
        ('Sustainability\ndebris slope ≤ 0\n(final 50 yr)',  C_BLUE),
        ('Capacity\ndebris < 30,000\n(at year 100)',         C_GREEN),
    ]
    col3_top = center_y + 1.4
    y_cursor = col3_top
    centers3 = []
    for label, color in threshold_rows:
        h = wrapped_box(col3_x, y_cursor, col3_w, label, color, fontsize=8)
        centers3.append((y_cursor, h))
        y_cursor -= (h + 0.18)

    for (yt, h), (yt2, h2) in zip(centers3[:-1], centers3[1:]):
        arrow(col3_x + col3_w/2, yt - h, col3_x + col3_w/2, yt2, color='#aaaaaa', lw=1.0)

    y_cursor -= 0.10
    h_robust = wrapped_box(col3_x, y_cursor, col3_w,
                            'Robustness Score\n% of 6 low-solar cells\npassing both thresholds',
                            '#444444', fontsize=8)
    arrow(col3_x + col3_w/2, centers3[-1][0] - centers3[-1][1], col3_x + col3_w/2, y_cursor, color='#aaaaaa', lw=1.0)
    col3_bottom = y_cursor - h_robust

    # Arrow column2 -> column3
    arrow(col2_x + col2_w, combo_center_y, col3_x - 0.05, combo_center_y, color='#888888', lw=1.4)

    # Title
    fig.suptitle('Formal campaign design: 16 governance configurations × 12 uncertainty cells = 192 runs',
                  fontsize=10.5, fontweight='bold', y=0.99)

    out = os.path.join(OUT_DIR, 'fig_4_2_campaign_design.png')
    plt.savefig(out, dpi=300, bbox_inches='tight')
    plt.close()
    print(f'Saved {out}')


if __name__ == '__main__':
    fig_5_1()
    r2 = fig_5_2()
    r4 = fig_5_4()
    fig_4_2()
    print('Done.')

    print('\n── Verification summary ──────────────────────────────────────────')
    print('Fig 5.2 — Market High vs Governance Failure (conservative/static atmosphere)')
    print('  Source: results/trajectory_timeseries.csv (illustrative trajectories;')
    print('          terminal values below are internal checks, not drawn on the figure)')
    print(f"  Market High run:        {r2['best_id']}")
    print(f"    legend label:         {r2['best_label']}")
    print(f"    terminal debris:      {r2['best_final']:,.1f}")
    print(f"  Governance Failure run: {r2['fail_id']}")
    print(f"    legend label:         {r2['fail_label']}")
    print(f"    terminal debris:      {r2['fail_final']:,.1f}")
    print(f"  Output: {r2['out']}")

    print('\nFig 5.4 — Behavioral fault line (solar=low, launch_growth=2.0)')
    for g, gid, rv, sv in zip(r4['groups'], r4['gov_ids'], r4['resp_vals'], r4['slug_vals']):
        print(f"  {g} ({gid}, low-solar, 2x launch growth):")
        print(f"    responsive: {rv:,.1f}")
        print(f"    sluggish:   {sv:,.1f}")
    print(f"  Output: {r4['out']}")
