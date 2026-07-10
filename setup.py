#!/usr/bin/env python
"""
Garmin Agent - Setup Script (Cross-platform)

Usage:
    python setup.py install   # Install dependencies
    python setup.py run       # Run the agent
    python setup.py clean     # Clean up
    python setup.py test      # Quick import test
    python setup.py help      # Show help
"""

import os
import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
VENV_DIR = PROJECT_ROOT / "venv"

is_windows = sys.platform.startswith("win")
SHELL = "cmd" if is_windows else "/bin/bash"


def run(cmd, *args, **kwargs):
    """Run a command in a subprocess."""
    kwargs.setdefault("check", True)
    print(f"  → {cmd}")
    subprocess.run(cmd, *args, **kwargs)


def run_shell(cmd, *args, **kwargs):
    """Run a shell command in a subprocess (intentionally uses shell=True)."""
    kwargs.setdefault("check", True)
    kwargs.setdefault("shell", True)
    print(f"  → {cmd}")
    subprocess.run(cmd, *args, **kwargs)


def ensure_venv():
    """Create virtual environment if needed."""
    if VENV_DIR.exists():
        print(f"  Virtual environment already exists at {VENV_DIR}/")
        return

    print(f"  Creating virtual environment...")
    run_shell(f"{sys.executable} -m venv {VENV_DIR}")


def get_python():
    """Get the python executable path in the venv."""
    if is_windows:
        return str(VENV_DIR / "Scripts" / "python.exe")
    return str(VENV_DIR / "bin" / "python")


def get_pip():
    """Get the pip executable path in the venv."""
    if is_windows:
        return str(VENV_DIR / "Scripts" / "pip.exe")
    return str(VENV_DIR / "bin" / "pip")


def install():
    """Install all dependencies."""
    print("Setting up Garmin Agent...")
    ensure_venv()
    pip = get_pip()
    run_shell(f"{pip} install --upgrade pip")
    run_shell(f"{pip} install -r {PROJECT_ROOT / 'requirements.txt'}")
    print("\n✅ Installation complete!\n")
    print("Next steps:")
    print("  1. Copy .env.example to .env and fill in your credentials")
    print(f"  2. Run: python {PROJECT_ROOT / 'main.py'}")


def run_agent():
    """Run the interactive agent."""
    if not VENV_DIR.exists():
        print("❌ Virtual environment not found. Run 'python setup.py install' first.")
        sys.exit(1)
    python = get_python()
    run_shell(f"{python} {PROJECT_ROOT / 'main.py'}")


def run_cli(command):
    """Run a CLI command."""
    if not VENV_DIR.exists():
        print("❌ Virtual environment not found. Run 'python setup.py install' first.")
        sys.exit(1)
    python = get_python()
    if command:
        # 使用参数列表调用，避免 shell 注入
        import subprocess
        subprocess.run(
            [python, str(PROJECT_ROOT / 'garmin_cli.py')] + command.split(),
            check=True
        )
    else:
        run_shell(f"{python} {PROJECT_ROOT / 'garmin_cli.py'} --help")


def test_imports():
    """Test that imports work correctly."""
    if not VENV_DIR.exists():
        print("❌ Virtual environment not found. Run 'python setup.py install' first.")
        sys.exit(1)
    python = get_python()
    run_shell(f"{python} -c \"from garmin_agent.agent import GarminAgent; print('✅ Import OK')\"")


def clean():
    """Clean up build artifacts."""
    import shutil
    if VENV_DIR.exists():
        shutil.rmtree(VENV_DIR)
        print(f"  Removed {VENV_DIR}/")

    # Clean __pycache__ directories
    for root, dirs, files in os.walk(PROJECT_ROOT):
        for d in dirs:
            if d == "__pycache__":
                shutil.rmtree(Path(root) / d)
                print(f"  Removed {Path(root) / d}/")

    print("Cleaned up.")


def show_help():
    """Show help message."""
    print("""
Garmin Agent Setup Script
==========================

Commands:
  install    - Create venv + install dependencies
  run        - Run the interactive agent
  cli <cmd>  - Run a CLI command (e.g., latest, health, capacity)
  test       - Quick import test
  clean      - Remove venv and __pycache__
  help       - Show this help

Usage:
  python setup.py install
  python setup.py run
  python setup.py cli latest
""")


def main():
    if len(sys.argv) < 2:
        show_help()
        return

    command = sys.argv[1]

    actions = {
        "install": install,
        "run": run_agent,
        "cli": lambda: run_cli(" ".join(sys.argv[2:]) if len(sys.argv) > 2 else run_cli(None)),
        "test": test_imports,
        "clean": clean,
        "help": show_help,
    }

    if command in actions:
        try:
            actions[command]()
        except subprocess.CalledProcessError as e:
            print(f"\n❌ Command failed with exit code {e.returncode}")
            sys.exit(e.returncode)
        except Exception as e:
            print(f"\n❌ Error: {e}")
            sys.exit(1)
    else:
        print(f"Unknown command: {command}")
        show_help()
        sys.exit(1)


if __name__ == "__main__":
    main()