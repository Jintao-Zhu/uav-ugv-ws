# Day8 Step 6.2 Debug Summary

## Problem
Coverage method with relay UGV consistently performs WORSE than greedy baseline across 10 seeds.

## Root Cause Analysis

### Issue 1: SNR Metric Bug (FIXED)
- **Problem**: Relay controller was receiving SNR_all (includes carrier) instead of SNR_nc (excludes carrier)
- **Impact**: Since UAV is always on carrier, SNR_all is always excellent, so relay never triggered
- **Fix**: Modified `_compute_greedy_goals()` to pass `snr_best_nc` to relay controller
- **Result**: Relay now triggers, but coverage still performs worse

### Issue 2: Fundamental Design Flaw (UNFIXED)
- **Problem**: The relay-based coverage approach is fundamentally flawed
- **Why**:
  1. Greedy naturally keeps UGVs clustered (motion = 1.02)
  2. This natural clustering is GOOD for communication
  3. Adding a relay UGV disrupts this clustering (motion increases to 1.18-1.23)
  4. The relay benefit doesn't compensate for the disruption
  5. Task execution suffers (miss rate increases from 0.6% to 3-4%)

## Experimental Results

### Test 1: risk_margin = 5.0 (default)
- Relay triggers: ~58% of steps
- Outage: 39.7% → 41.0% (WORSE by 1.3%)
- Positive seeds: 4/10
- **Conclusion**: Relay triggers too often, disrupts task execution

### Test 2: risk_margin = 2.0
- Relay triggers: ~40% of steps (estimated)
- Outage: 39.7% → 42.4% (WORSE by 2.7%)
- Positive seeds: 5/10
- **Conclusion**: Still triggers too often

### Test 3: risk_margin = 0.0
- Relay triggers: ~10% of steps (estimated)
- Outage: 39.7% → 39.7% (NO CHANGE)
- Positive seeds: 5/10
- Miss rate: 0.6% → 4.0% (MUCH WORSE)
- **Conclusion**: Relay barely triggers, but task execution still suffers

## Key Insights

1. **Greedy is naturally communication-friendly**: Low motion (1.02) means UGVs stay close together
2. **Coverage disrupts natural clustering**: Motion increases to 1.18-1.23
3. **Relay can't compensate**: Even when relay works, it doesn't offset the clustering disruption
4. **Task execution suffers**: Miss rate increases significantly (0.6% → 3-4%)

## Validation Criteria (All Failed)
1. ❌ Outage_NC 显著降低 (≥30% relative or ≥5% absolute): Best was -2.7%
2. ✅ Tasks 不塌陷 (<20% decrease): Passed (only -0.4% to -0.6%)
3. ❌ 大多数 seed 正向改善 (≥70%): Only 40-50% of seeds improved

## Recommendations

### Option 1: Abandon Relay Approach
- Accept that greedy's natural clustering is already optimal
- Focus on other improvements (e.g., better task assignment, MAPF)

### Option 2: Communication-Aware Greedy
- Modify greedy to explicitly consider communication when assigning tasks
- Penalize task assignments that would spread UGVs too far apart
- Keep all UGVs doing tasks (no dedicated relay)

### Option 3: Hybrid Approach
- Use relay only in extreme cases (e.g., when outage > 50%)
- Make relay UGV also do tasks most of the time
- Requires more sophisticated triggering logic

### Option 4: Different Relay Strategy
- Instead of one dedicated relay UGV, make ALL UGVs communication-aware
- Each UGV considers both task value and communication impact
- No dedicated relay, but all UGVs help maintain connectivity

## Next Steps

Need to discuss with user:
1. Should we abandon the relay approach?
2. Should we try communication-aware greedy instead?
3. Should we adjust validation criteria to be more realistic?
4. Should we continue with Step 6.3 (dual threshold testing) despite failures?
