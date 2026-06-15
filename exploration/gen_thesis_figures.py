"""
Generate two thesis conceptual figures:
  fig_3_1_conceptual_framework.png  — governance → parameters → dynamics → outcomes
  fig_4_2_pyssem_schematic.png      — pySSEM species / shell / source-sink structure
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'figures', 'thesis')
os.makedirs(OUT_DIR, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# Figure 3.1 — Conceptual Framework
# ─────────────────────────────────────────────────────────────────────────────

def fig_3_1():
    fig, ax = plt.subplots(figsize=(13, 7))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 7)
    ax.axis('off')

    # ── colour palette ────────────────────────────────────────────────────────
    C = {
        'gov':      '#2c5f8a',   # dark blue
        'param':    '#27706b',   # teal
        'sim':      '#5a3d8a',   # purple
        'outcome':  '#1a6b2a',   # green
        'fail':     '#8a2222',   # red
        'uncert':   '#b08000',   # gold
        'arrow':    '#444444',
        'bg':       '#f8f8f8',
    }

    def box(ax, x, y, w, h, label, sublabel=None, color='#2c5f8a', fontsize=9):
        rect = FancyBboxPatch((x, y), w, h,
                              boxstyle='round,pad=0.08',
                              facecolor=color, edgecolor='white',
                              linewidth=1.5, alpha=0.92, zorder=3)
        ax.add_patch(rect)
        cy = y + h/2 + (0.15 if sublabel else 0)
        ax.text(x + w/2, cy, label,
                ha='center', va='center', fontsize=fontsize,
                fontweight='bold', color='white', zorder=4)
        if sublabel:
            ax.text(x + w/2, y + h/2 - 0.22, sublabel,
                    ha='center', va='center', fontsize=7.2,
                    color='white', alpha=0.88, zorder=4, style='italic')

    def arrow(ax, x0, y0, x1, y1, color='#444444', lw=1.6):
        ax.annotate('', xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle='->', color=color,
                                   lw=lw, connectionstyle='arc3,rad=0.0'),
                    zorder=2)

    # ── Column headers ────────────────────────────────────────────────────────
    headers = [
        (0.4,  'Governance\nCategories'),
        (3.3,  'Behavioral\nParameters'),
        (6.15, 'pySSEM\nSimulation'),
        (9.1,  'Orbital\nOutcomes'),
    ]
    for xh, label in headers:
        ax.text(xh + 1.15, 6.60, label, ha='center', va='center',
                fontsize=9.5, fontweight='bold', color='#333333')

    # ── Governance category boxes (col 1) ─────────────────────────────────────
    gov_boxes = [
        (0.35, 5.45, 'Command &\nControl',    '(Pm, deltat)'),
        (0.35, 4.10, 'Market-\nBased',        '(Pm, launch)'),
        (0.35, 2.75, 'Liability &\nEnforcement', '(Pm indirect)'),
        (0.35, 1.40, 'Coordination\n& STM',   '(alpha, slotting)'),
    ]
    for gx, gy, lbl, sub in gov_boxes:
        box(ax, gx, gy, 2.35, 0.95, lbl, sub, color=C['gov'], fontsize=8.5)

    # ── Parameter boxes (col 2) ───────────────────────────────────────────────
    param_data = [
        (3.20, 5.30, 'Pm',         'PMD compliance\n(dominant)'),
        (3.20, 3.95, 'Launch rate','orbital access\nvolume'),
        (3.20, 2.60, 'deltat',     'years derelict\nif PMD fails'),
        (3.20, 1.25, 'alpha /\nslotting', 'CA failure rate\n(negligible)'),
    ]
    for px, py, lbl, sub in param_data:
        box(ax, px, py, 2.35, 0.95, lbl, sub, color=C['param'], fontsize=8.5)

    # ── pySSEM simulation box (col 3) ─────────────────────────────────────────
    box(ax, 6.10, 1.10, 2.35, 4.90, '', color=C['sim'])
    ax.text(7.275, 3.55, 'pySSEM\nODE Model', ha='center', va='center',
            fontsize=10, fontweight='bold', color='white', zorder=5)
    for label, yy in [('S  Active sats', 4.70), ('N  Debris', 3.95),
                       ('B  Rocket bodies', 3.20), ('40 shells', 2.45),
                       ('200–1200 km', 2.05), ('100-year horizon', 1.65)]:
        ax.text(7.275, yy, label, ha='center', va='center',
                fontsize=7.5, color='white', alpha=0.85, zorder=5)

    # ── Outcome boxes (col 4) ─────────────────────────────────────────────────
    box(ax, 9.05, 4.50, 2.35, 1.50, 'Sustainable', 'slope ≤ 0\n(final 50 yr)',
        color=C['outcome'], fontsize=8.5)
    box(ax, 9.05, 2.80, 2.35, 1.50, 'Capacity OK', '< 30,000\ndebris',
        color=C['outcome'], fontsize=8.5)
    box(ax, 9.05, 1.10, 2.35, 1.50, 'Both / Neither',
        'robustness\nassessment', color=C['fail'], fontsize=8.5)

    # ── Uncertainty band (col 3.5, overlapping) ───────────────────────────────
    unc_rect = FancyBboxPatch((5.65, 0.40), 6.10, 6.00,
                              boxstyle='round,pad=0.08',
                              facecolor='none', edgecolor=C['uncert'],
                              linewidth=2.0, linestyle='--', alpha=0.75, zorder=1)
    ax.add_patch(unc_rect)
    ax.text(8.70, 6.50, 'Uncertainty space',
            ha='center', va='center', fontsize=8, color=C['uncert'],
            fontweight='bold', style='italic')

    # Uncertainty sub-labels
    for xt, yt, txt in [
        (8.0,  0.62, 'Solar: static_exp / JB2008'),
        (10.0, 0.62, 'Behavior: responsive / sluggish'),
    ]:
        ax.text(xt, yt, txt, ha='center', va='center', fontsize=7.2,
                color=C['uncert'], style='italic')

    # ── Arrows: gov → param ───────────────────────────────────────────────────
    gov_cx = 0.35 + 2.35   # right edge of gov boxes
    param_lx = 3.20         # left edge of param boxes

    # Pm: C&C, Market, Liability all → Pm
    for gy in [5.93, 4.58, 3.23]:
        arrow(ax, gov_cx, gy, param_lx, 5.78)
    # Launch: Market → launch
    arrow(ax, gov_cx, 4.58, param_lx, 4.43)
    # deltat: C&C → deltat
    arrow(ax, gov_cx, 5.93, param_lx, 3.08)
    # alpha/slotting: Coordination → alpha/slotting
    arrow(ax, gov_cx, 1.88, param_lx, 1.73)

    # ── Arrows: param → sim ───────────────────────────────────────────────────
    param_cx = 3.20 + 2.35
    sim_lx   = 6.10
    for py in [5.78, 4.43, 3.08, 1.73]:
        arrow(ax, param_cx, py, sim_lx, 3.55)

    # ── Arrow: sim → outcomes ─────────────────────────────────────────────────
    sim_cx = 6.10 + 2.35
    for oy in [5.25, 3.55, 1.85]:
        arrow(ax, sim_cx, 3.55, 9.05, oy)

    # ── Title ─────────────────────────────────────────────────────────────────
    ax.text(6.5, 6.90, 'Conceptual Framework: Governance → Simulation → Outcomes',
            ha='center', va='center', fontsize=11, fontweight='bold', color='#222222')

    plt.tight_layout(pad=0.3)
    out = os.path.join(OUT_DIR, 'fig_3_1_conceptual_framework.png')
    plt.savefig(out, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f'Saved {out}')


# ─────────────────────────────────────────────────────────────────────────────
# Figure 4.2 — pySSEM Model Schematic
# ─────────────────────────────────────────────────────────────────────────────

def fig_4_2():
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.axis('off')

    C = {
        'S':      '#2980b9',   # active sats — blue
        'N':      '#c0392b',   # debris — red
        'B':      '#7f8c8d',   # rocket bodies — grey
        'shell':  '#ecf0f1',
        'border': '#bdc3c7',
        'arrow':  '#555555',
        'launch': '#27ae60',
        'decay':  '#8e44ad',
        'coll':   '#e67e22',
        'bg':     '#fdfdfd',
    }

    def rbox(ax, x, y, w, h, label, color, fontsize=8.5, alpha=0.90):
        rect = FancyBboxPatch((x, y), w, h,
                              boxstyle='round,pad=0.07',
                              facecolor=color, edgecolor='white',
                              linewidth=1.2, alpha=alpha, zorder=4)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h/2, label, ha='center', va='center',
                fontsize=fontsize, fontweight='bold', color='white', zorder=5)

    def arr(ax, x0, y0, x1, y1, color='#555555', lw=1.4,
            label='', lcolor='#333333', lsize=7.5):
        ax.annotate('', xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle='->', color=color,
                                   lw=lw, connectionstyle='arc3,rad=0.0'),
                    zorder=3)
        if label:
            mx, my = (x0+x1)/2, (y0+y1)/2
            ax.text(mx, my, label, ha='center', va='center',
                    fontsize=lsize, color=lcolor, zorder=6,
                    bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, pad=1))

    # ── Shell stack ───────────────────────────────────────────────────────────
    shell_heights = [0.62] * 5
    shell_ys = [1.30, 2.05, 2.80, 3.55, 4.30]
    shell_labels = ['Shell 1\n~200 km', 'Shell 2\n~400 km',
                    'Shell 3\n~600 km', '  ...', 'Shell 40\n~1200 km']
    shell_x = 3.20
    shell_w = 5.60

    for i, (sy, slbl) in enumerate(zip(shell_ys, shell_labels)):
        col = C['shell'] if i % 2 == 0 else '#e8eef4'
        rect = FancyBboxPatch((shell_x, sy), shell_w, shell_heights[i],
                              boxstyle='round,pad=0.04',
                              facecolor=col, edgecolor=C['border'],
                              linewidth=1.0, alpha=0.95, zorder=2)
        ax.add_patch(rect)
        ax.text(shell_x + 0.35, sy + shell_heights[i]/2, slbl,
                ha='left', va='center', fontsize=7.5, color='#333333', zorder=3)

        if i < 3:   # Show species boxes in first 3 shells
            # S box
            rbox(ax, shell_x + 1.45, sy + 0.08, 1.10, 0.46,
                 'S (sats)', C['S'], fontsize=7.5)
            # N box
            rbox(ax, shell_x + 2.70, sy + 0.08, 1.10, 0.46,
                 'N (debris)', C['N'], fontsize=7.5)
            # B box
            rbox(ax, shell_x + 3.95, sy + 0.08, 1.10, 0.46,
                 'B (RBs)', C['B'], fontsize=7.5)

    # Ellipsis for hidden shells
    ax.text(shell_x + shell_w/2, 3.65, '· · ·',
            ha='center', va='center', fontsize=14, color='#999999')

    # ── Left panel: ODE integrator ────────────────────────────────────────────
    rbox(ax, 0.25, 3.00, 2.60, 1.20, 'BDF ODE\nIntegrator', '#34495e', fontsize=9)
    ax.text(1.55, 2.80, 'Source-sink\nper species per shell',
            ha='center', va='center', fontsize=7.0, color='#555555', style='italic')

    arr(ax, 2.85, 3.60, shell_x, 3.60, color=C['arrow'], lw=1.4)

    # ── Right panel: atmospheric drag & collision ─────────────────────────────
    rbox(ax, 9.15, 4.30, 2.60, 0.85, 'Atmospheric\nDrag', C['decay'], fontsize=8.5)
    rbox(ax, 9.15, 3.20, 2.60, 0.85, 'Collision\nFragmentation', C['coll'], fontsize=8.5)
    rbox(ax, 9.15, 2.10, 2.60, 0.85, 'PMD Disposal\n(Pm parameter)', C['S'], fontsize=8.5)

    shell_rx = shell_x + shell_w
    arr(ax, shell_rx, 4.60, 9.15, 4.72, color=C['decay'])
    arr(ax, shell_rx, 3.50, 9.15, 3.62, color=C['coll'])
    arr(ax, shell_rx, 2.40, 9.15, 2.52, color=C['S'])

    # ── Top: launch inputs ────────────────────────────────────────────────────
    rbox(ax, 3.20, 5.60, 2.20, 0.70, 'Launch rates\n(SEP2 scenario)', C['launch'], fontsize=8)
    arr(ax, 4.30, 5.60, 4.30, 5.24 + shell_heights[-1],
        color=C['launch'], label='new sats', lcolor=C['launch'])

    rbox(ax, 6.40, 5.60, 2.40, 0.70, 'Atmospheric density\n(static_exp / JB2008)', '#7d6608', fontsize=7.5)
    arr(ax, 7.60, 5.60, 7.60, 5.24 + shell_heights[-1],
        color='#7d6608', label='drag rate', lcolor='#7d6608')

    # ── Bottom: outputs ───────────────────────────────────────────────────────
    rbox(ax, 3.20, 0.25, 2.20, 0.75, 'Debris stock\nover time', C['N'], fontsize=8)
    rbox(ax, 6.00, 0.25, 2.00, 0.75, 'Sat population\nover time', C['S'], fontsize=8)
    rbox(ax, 8.60, 0.25, 2.15, 0.75, 'Collision\nevents', C['coll'], fontsize=8)

    for ox in [4.30, 7.00, 9.675]:
        arr(ax, ox, shell_ys[0], ox, 1.00, color='#888888')

    # ── Vertical inter-shell cascade arrow ────────────────────────────────────
    ax.annotate('', xy=(2.95, 2.20), xytext=(2.95, 4.55),
                arrowprops=dict(arrowstyle='->', color='#888888',
                                lw=1.2, connectionstyle='arc3,rad=0.0'), zorder=2)
    ax.text(2.70, 3.38, 'Shell\ncascade', ha='center', va='center',
            fontsize=7.0, color='#777777', style='italic', rotation=90)

    # ── Legend ────────────────────────────────────────────────────────────────
    legend_items = [
        (C['S'],     'S — Active satellites'),
        (C['N'],     'N — Debris (multiple mass bins)'),
        (C['B'],     'B — Rocket bodies'),
        (C['launch'],'Launch input (SEP2)'),
        (C['decay'], 'Atmospheric decay'),
        (C['coll'],  'Collision fragmentation'),
    ]
    lx, ly = 0.25, 2.30
    for i, (col, lbl) in enumerate(legend_items):
        yy = ly - i * 0.33
        ax.add_patch(plt.Rectangle((lx, yy - 0.10), 0.22, 0.22,
                                   facecolor=col, edgecolor='white',
                                   linewidth=0.8, zorder=6))
        ax.text(lx + 0.30, yy + 0.01, lbl, va='center', fontsize=7.0,
                color='#333333', zorder=6)

    # ── Title ─────────────────────────────────────────────────────────────────
    ax.text(6.0, 7.70, 'pySSEM Model Structure — Species, Shells, and Source-Sink Flows',
            ha='center', va='center', fontsize=11, fontweight='bold', color='#222222')

    ax.text(6.0, 7.35,
            '40 altitude shells (200–1200 km) × 3 species groups (S, N, B) × BDF ODE, 100-year horizon',
            ha='center', va='center', fontsize=8, color='#555555', style='italic')

    plt.tight_layout(pad=0.3)
    out = os.path.join(OUT_DIR, 'fig_4_2_pyssem_schematic.png')
    plt.savefig(out, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f'Saved {out}')


if __name__ == '__main__':
    fig_3_1()
    fig_4_2()
    print('Done.')
