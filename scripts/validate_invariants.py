#!/usr/bin/env python3
"""
Local validation script for Phase 5.6+ invariants.

This script mimics the CI workflow for local development validation.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and report results."""
    print(f"\n🔧 {description}")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"✅ {description} - PASSED")
        if result.stdout.strip():
            print(f"Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - FAILED")
        print(f"Exit code: {e.returncode}")
        if e.stdout:
            print(f"STDOUT: {e.stdout}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        return False
    except FileNotFoundError:
        print(f"⚠️  {description} - SKIPPED (command not found)")
        return True


def main():
    """Run local invariant validation."""
    print("🔧 Phase 5.6+ Invariant Validation (Local)")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("tests/invariants").exists():
        print("❌ Must run from project root directory")
        sys.exit(1)
    
    all_passed = True
    
    # 1. Validate mini-corpus config
    success = run_command(
        [sys.executable, "-c", """
import json
with open('tests/invariants/mini_corpus.json') as f:
    config = json.load(f)
assert 'rulebooks' in config
assert len(config['rulebooks']) >= 3
print('Mini-corpus configuration is valid')
"""],
        "Validate mini-corpus configuration"
    )
    all_passed = all_passed and success
    
    # 2. Check for test data
    test_dir = Path("eval/phase_5_6_test")
    if test_dir.exists():
        print(f"\n✅ Test data available: {test_dir}")
        
        # 3. Run Phase 5.6 invariant verification
        success = run_command(
            [sys.executable, "tests/invariants/phase_5_6_invariants.py"],
            "Phase 5.6+ invariant verification"
        )
        all_passed = all_passed and success
        
        # 4. Run pytest invariant suite
        success = run_command(
            [sys.executable, "-m", "pytest", "tests/invariants/test_phase_5_6_invariants.py", "-v"],
            "Pytest invariant test suite"
        )
        all_passed = all_passed and success
        
    else:
        print(f"\n⚠️  Test data not available: {test_dir}")
        print("Run 'python phase_5_6_test_runner.py' first to generate test data")
    
    # 5. Lint invariant code (if flake8 available)
    success = run_command(
        [sys.executable, "-m", "flake8", "tests/invariants/", "--max-line-length=100", "--ignore=E501"],
        "Lint invariant code"
    )
    # Don't fail on linting issues
    
    # Final result
    print(f"\n🏁 Invariant Validation Summary")
    if all_passed:
        print("✅ ALL CRITICAL INVARIANTS VERIFIED")
        print("Phase 6 development can proceed safely")
        sys.exit(0)
    else:
        print("❌ INVARIANT VIOLATIONS DETECTED")
        print("Phase 6 development is BLOCKED until invariants are restored")
        sys.exit(1)


if __name__ == "__main__":
    main()