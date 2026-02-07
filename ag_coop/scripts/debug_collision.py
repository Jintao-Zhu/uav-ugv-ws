"""
Debug script: Reproduce the collision from seed=0 at t=113

This script will:
1. Set up the exact scenario from t=110
2. Call MAPF with the positions and goals at t=110
3. Check if the returned paths have collisions
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agcoop.mapf import MAPFPlanner
from agcoop.map import auto_load_map


def check_collision(paths, n):
    """Check for collisions in paths"""
    if not paths:
        return True, ""

    max_len = max(len(path) for path in paths.values())

    for t in range(max_len):
        positions_at_t = {}
        for agent_id in range(n):
            if t < len(paths[agent_id]):
                pos = paths[agent_id][t]
            else:
                pos = paths[agent_id][-1]

            if pos in positions_at_t.values():
                other_agent = [aid for aid, p in positions_at_t.items() if p == pos][0]
                return False, f"Vertex collision at t={t}: agent {agent_id} and {other_agent} at {pos}"

            positions_at_t[agent_id] = pos

        if t > 0:
            for agent_id in range(n):
                if t < len(paths[agent_id]):
                    prev_pos = paths[agent_id][t-1]
                    curr_pos = paths[agent_id][t]
                else:
                    continue

                for other_id in range(n):
                    if other_id == agent_id:
                        continue

                    if t < len(paths[other_id]):
                        other_prev = paths[other_id][t-1]
                        other_curr = paths[other_id][t]

                        if prev_pos == other_curr and curr_pos == other_prev:
                            return False, f"Edge collision at t={t}: agent {agent_id} and {other_id} swap"

    return True, ""


def main():
    print("=" * 80)
    print("Debug: Reproduce collision from seed=0 at t=113")
    print("=" * 80)
    print()

    # Load map
    map_path = project_root / "maps" / "map_01.map"
    grid_map = auto_load_map(str(map_path))

    # Create planner
    planner = MAPFPlanner(
        grid_map=grid_map,
        connectivity=4,
        time_budget_ms=300
    )

    # Scenario at t=110 (from the error log)
    # We need to figure out what the positions were at t=110
    # From the error: at t=113, prev_positions = [(17, 4), (18, 15), (18, 16)]
    # So at t=112, positions = [(17, 4), (18, 15), (18, 16)]
    # Working backwards: t=110 positions would be 2 steps before

    # Let's use the positions from the error and work backwards
    # Actually, let's just test if agent 2 at goal causes issues

    starts = {
        0: (17, 6),   # Agent 0 a few steps from goal
        1: (18, 13),  # Agent 1 far from goal
        2: (18, 16)   # Agent 2 already at goal
    }

    goals = {
        0: (17, 3),
        1: (18, 17),
        2: (18, 16)
    }

    print(f"Starts: {starts}")
    print(f"Goals: {goals}")
    print()
    print("Note: Agent 2 is already at its goal")
    print()

    # Plan MAPF
    result = planner.plan_mapf(
        starts=starts,
        goals=goals,
        H=40,
        priority_order=[0, 1, 2]
    )

    print(f"MAPF Success: {result.success}")
    print(f"Solve time: {result.solve_time_ms:.2f} ms")
    print()

    if result.success:
        # Print paths
        for agent_id in range(3):
            path = result.paths[agent_id]
            print(f"Agent {agent_id} path (length {len(path)}):")
            print(f"  First 10: {path[:10]}")
            print(f"  Last 5: {path[-5:]}")
            print()

        # Check collision
        collision_free, error = check_collision(result.paths, 3)
        if collision_free:
            print("✓ No collisions in planned paths")
        else:
            print(f"✗ COLLISION FOUND: {error}")
            print()
            print("This confirms the MAPF planner has a bug!")
    else:
        print(f"✗ MAPF failed: {result.failure_reason}")


if __name__ == "__main__":
    main()
