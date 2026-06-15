# Table 6.1 — Governance Performance Under Low-Solar Uncertainty (6 low-solar cells)

Sorted by robustness (% passing both thresholds, descending).
Thresholds: debris slope ≤ 0 (final 50yr) AND total debris < 30,000.

| Gov. Config | Category | Level | Mean Debris | Min Debris | Max Debris | % Sustainable | % Capacity OK | % Both OK |
|---|---|---|---:|---:|---:|---:|---:|---:|
| mkt_high | Market | High | 19,981 | 10,355 | 37,507 | 83% | 83% | **83%** |
| cnc_high | C&C | High | 33,795 | 12,717 | 73,824 | 67% | 67% | **67%** |
| lib_high | Liability | High | 33,684 | 12,726 | 73,383 | 67% | 67% | **67%** |
| mix_fees_enf | Mix | Fees+Enforce | 33,036 | 15,156 | 62,880 | 67% | 50% | **50%** |
| mix_all | Mix | All Four | 33,097 | 15,167 | 63,049 | 67% | 50% | **50%** |
| stm_low | Coordination | Low | 42,752 | 17,640 | 85,397 | 50% | 33% | **33%** |
| stm_med | Coordination | Medium | 42,748 | 17,628 | 85,727 | 50% | 33% | **33%** |
| stm_high | Coordination | High | 42,726 | 17,621 | 85,394 | 50% | 33% | **33%** |
| mkt_med | Market | Medium | 39,991 | 18,906 | 71,924 | 50% | 33% | **33%** |
| mix_rules_stm | Mix | Rules+Coord | 52,460 | 22,731 | 98,161 | 33% | 17% | **17%** |
| lib_med | Liability | Medium | 62,856 | 28,045 | 111,965 | 17% | 17% | **17%** |
| cnc_med | C&C | Medium | 61,932 | 27,950 | 109,744 | 0% | 17% | **0%** |
| cnc_low | C&C | Low | 97,017 | 47,392 | 149,870 | 0% | 0% | **0%** |
| mkt_low | Market | Low | 85,291 | 39,246 | 141,054 | 0% | 0% | **0%** |
| lib_low | Liability | Low | 97,535 | 45,084 | 158,139 | 0% | 0% | **0%** |
| failure | Failure | — | 266,310 | 106,403 | 445,905 | 0% | 0% | **0%** |

**Notes:**
- Low-solar = static_exp atmospheric density model (conservative, lower drag, slower debris decay)
- Each config evaluated across 6 cells: 3 launch growths (1×/2×/3×) × 2 behavioral responses (responsive/sluggish)
- Coordination configs (stm_low/med/high) are statistically identical — range < 20 debris objects across all three
- mkt_high is the only config that fails in exactly one cell (sluggish + 3× growth)
