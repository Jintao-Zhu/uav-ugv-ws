#!/usr/bin/env python3
"""
Day10 Step 6: Delivery Package Verification Script

Verifies that all required files are present and valid.
"""

import json
import os
import sys
from pathlib import Path

def verify_delivery_package():
    """Verify Day10 delivery package completeness."""

    package_dir = Path("outputs/day10_ppo_summary")

    print("=" * 60)
    print("Day10 Delivery Package Verification")
    print("=" * 60)
    print()

    # Required files
    required_files = {
        "train_config.yaml": "Training configuration (YAML)",
        "train_config.json": "Training configuration (JSON)",
        "eval_random.json": "Random policy evaluation",
        "eval_ppo.json": "PPO policy evaluation",
        "summary.md": "Comprehensive summary",
        "best_model.zip": "Trained PPO model",
        "README.md": "Package documentation"
    }

    all_present = True

    print("📋 File Checklist:")
    print("-" * 60)

    for filename, description in required_files.items():
        filepath = package_dir / filename
        if filepath.exists():
            size = filepath.stat().st_size
            size_kb = size / 1024
            print(f"✅ {filename:25s} ({size_kb:6.1f} KB) - {description}")
        else:
            print(f"❌ {filename:25s} MISSING - {description}")
            all_present = False

    print()

    if not all_present:
        print("❌ Verification FAILED: Missing required files")
        return False

    # Verify JSON files are valid
    print("🔍 JSON Validation:")
    print("-" * 60)

    json_files = ["train_config.json", "eval_random.json", "eval_ppo.json"]
    json_valid = True

    for filename in json_files:
        filepath = package_dir / filename
        try:
            with open(filepath) as f:
                data = json.load(f)
            print(f"✅ {filename:25s} Valid JSON")
        except Exception as e:
            print(f"❌ {filename:25s} Invalid: {e}")
            json_valid = False

    print()

    if not json_valid:
        print("❌ Verification FAILED: Invalid JSON files")
        return False

    # Verify evaluation results
    print("📊 Evaluation Results:")
    print("-" * 60)

    try:
        with open(package_dir / "eval_random.json") as f:
            random_data = json.load(f)
        with open(package_dir / "eval_ppo.json") as f:
            ppo_data = json.load(f)

        random_reward = random_data["summary"]["mean_total_reward"]
        ppo_reward = ppo_data["summary"]["mean_total_reward"]
        improvement = ((ppo_reward - random_reward) / random_reward) * 100

        print(f"Random Policy Mean Reward:  {random_reward:.2f}")
        print(f"PPO Policy Mean Reward:     {ppo_reward:.2f}")
        print(f"Improvement:                +{improvement:.2f}%")
        print()

        if improvement >= 5.0:
            print(f"✅ Performance requirement met (+{improvement:.2f}% ≥ 5%)")
        else:
            print(f"❌ Performance requirement NOT met (+{improvement:.2f}% < 5%)")
            return False

        # Check for NaN/Inf
        has_nan_inf = ppo_data["summary"].get("has_nan_inf", False)
        if not has_nan_inf:
            print("✅ No NaN/Inf detected in PPO rollouts")
        else:
            print("❌ NaN/Inf detected in PPO rollouts")
            return False

        # Check episode count
        n_episodes = len(ppo_data["episodes"])
        if n_episodes == 5:
            print(f"✅ All 5 evaluation episodes completed")
        else:
            print(f"❌ Only {n_episodes}/5 episodes completed")
            return False

    except Exception as e:
        print(f"❌ Error reading evaluation results: {e}")
        return False

    print()

    # Summary
    print("=" * 60)
    print("✅ Day10 Delivery Package Verification PASSED")
    print("=" * 60)
    print()
    print("Package Location: outputs/day10_ppo_summary/")
    print("Total Files:      7")
    print(f"Total Size:       ~{sum(f.stat().st_size for f in package_dir.glob('*')) / 1024:.0f} KB")
    print()
    print("Next Steps:")
    print("  1. Review summary.md for complete documentation")
    print("  2. Load best_model.zip for inference")
    print("  3. Use train_config.yaml to reproduce training")
    print()

    return True

if __name__ == "__main__":
    success = verify_delivery_package()
    sys.exit(0 if success else 1)
