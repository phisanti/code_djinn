#!/usr/bin/env python3
"""
Quick release preparation script for CodeDjinn.

This script helps prepare a release by running checks and providing
guidance on the release process.
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, description, check=True):
    """Run a command and print the result."""
    print(f"\n🔍 {description}")
    print(f"Running: {' '.join(cmd)}")
    print("-" * 50)

    try:
        result = subprocess.run(cmd, check=check, capture_output=False)
        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
        else:
            print(f"❌ {description} - FAILED")
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - FAILED with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        print(f"❌ {description} - Command not found")
        return False


def check_version_consistency():
    """Check that versions are consistent across files."""
    print("\n🔍 Checking version consistency")
    print("-" * 50)

    # Read setup.py version
    setup_version = None
    try:
        with open("setup.py", "r") as f:
            for line in f:
                if line.strip().startswith("version="):
                    setup_version = line.split('"')[1]
                    break
    except FileNotFoundError:
        print("❌ setup.py not found")
        return False

    # Read pyproject.toml version
    pyproject_version = None
    try:
        with open("pyproject.toml", "r") as f:
            for line in f:
                if line.strip().startswith("version ="):
                    pyproject_version = line.split('"')[1]
                    break
    except FileNotFoundError:
        print("❌ pyproject.toml not found")
        return False

    if setup_version and pyproject_version:
        if setup_version == pyproject_version:
            print(f"✅ Version consistency - Both files have version {setup_version}")
            return True
        else:
            print(
                f"❌ Version mismatch: setup.py={setup_version}, pyproject.toml={pyproject_version}"
            )
            return False
    else:
        print("❌ Could not extract versions from files")
        return False


def main():
    """Main release preparation function."""
    print("🚀 CodeDjinn Release Preparation")
    print("=" * 60)

    # Change to project directory
    project_root = Path(__file__).parent
    os.chdir(project_root)

    # Track success of all checks
    all_checks_passed = True

    # 1. Check version consistency
    all_checks_passed &= check_version_consistency()

    # 2. Run tests
    all_checks_passed &= run_command(
        [sys.executable, os.path.join("scripts", "run_tests.py")], "Running unit tests"
    )

    # 3. Check package can be imported
    all_checks_passed &= run_command(
        [
            sys.executable,
            "-c",
            "import codedjinn; print('✅ Package imports successfully')",
        ],
        "Testing package import",
    )

    # 4. Test package build
    print("\n🔍 Testing package build")
    print("-" * 50)

    # Clean old build artifacts
    run_command(
        ["rm", "-rf", "dist/", "build/", "*.egg-info/"],
        "Cleaning build artifacts",
        check=False,
    )

    # Build package
    all_checks_passed &= run_command(
        [sys.executable, "-m", "build"], "Building package"
    )

    # 5. Check package integrity
    all_checks_passed &= run_command(
        [sys.executable, "-m", "twine", "check", "dist/*"], "Checking package integrity"
    )

    # 6. Display results
    print("\n" + "=" * 60)
    if all_checks_passed:
        print("🎉 All checks passed! Ready for release.")
        print("\nNext steps:")
        print("1. Commit any final changes")
        print("2. Create and push a git tag: git tag vX.Y.Z && git push origin vX.Y.Z")
        print("3. Create a GitHub release to trigger automatic PyPI publishing")
        print("4. Monitor the GitHub Actions workflow")
    else:
        print("❌ Some checks failed. Please fix issues before releasing.")
        print("\nFailed checks need to be resolved before creating a release.")

    print("\n📋 Release checklist:")
    print("   □ All tests pass")
    print("   □ Version numbers updated in setup.py and pyproject.toml")
    print("   □ RELEASE.md or release notes prepared")
    print("   □ No critical issues or bugs")
    print("   □ Documentation updated if needed")

    return 0 if all_checks_passed else 1


if __name__ == "__main__":
    sys.exit(main())
