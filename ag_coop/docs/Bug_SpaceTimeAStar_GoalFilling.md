# Bug Report: Space-Time A* Goal Filling Collision

## Summary
Critical bug in `agcoop/mapf/astar.py`: When an agent reaches its goal early, the path is filled to H+1 length without checking if future timesteps are reserved by other agents, causing collisions.

## Root Cause
In `SpaceTimeAStar.search()`, lines 161-163:

```python
# 如果路径长度小于 H+1，在目标位置 stay
while len(path) <= H:
    path.append(goal)
```

This fills the path by appending the goal position for all remaining timesteps up to H, **without checking the reservation table**. This violates the constraint that agents should not occupy positions reserved by other agents.

## Reproduction
```python
# Agent 1 plans first, reserves (18, 16) at t=3
# Agent 2 plans second with start == goal == (18, 16)
# Agent 2 reaches goal at t=0, fills path with (18, 16) for t=0..40
# Result: Both agents at (18, 16) at t=3 → COLLISION
```

See `scripts/debug_collision.py` for minimal reproduction.

## Impact
- **Severity**: Critical
- **Affected**: All MAPF planning with prioritized agents
- **Manifestation**: Vertex collisions when lower-priority agents are already at their goal
- **Test failures**: 4/10 seeds in statistical validation (Test D)

## Fix Strategy

### Option 1: Check reservations during filling (Simple)
```python
while len(path) <= H:
    t = len(path)
    if self.reservation_table.is_vertex_free(goal, t, agent_id):
        path.append(goal)
    else:
        # Goal is reserved by another agent, cannot stay
        return None, False, expanded_nodes
```

**Pros**: Simple, minimal change
**Cons**: Fails when goal is temporarily reserved (even if agent will leave later)

### Option 2: Continue search until H (Correct)
```python
# Don't return immediately when reaching goal
# Instead, mark goal_reached = True and continue searching
# Only return when t >= H
```

**Pros**: Finds valid paths even when goal is temporarily occupied
**Cons**: More complex, requires refactoring the search loop

### Option 3: WAIT at a safe position (Robust)
```python
# When goal is reserved, find a nearby safe position to wait
# Then move to goal when it becomes free
```

**Pros**: Most robust, handles complex scenarios
**Cons**: Most complex, may require multiple iterations

## Recommended Fix
**Option 2** - Continue search until H. This is the correct behavior for Space-Time A* in a prioritized MAPF setting.

## Test Cases to Verify Fix
1. Agent already at goal (start == goal)
2. Agent reaches goal early (before H)
3. Goal temporarily occupied by higher-priority agent
4. Goal permanently occupied (should fail gracefully)

## Related Files
- `agcoop/mapf/astar.py` (lines 156-165)
- `scripts/debug_collision.py` (reproduction)
- `scripts/test_mapf_integration.py` (integration test that exposed the bug)
