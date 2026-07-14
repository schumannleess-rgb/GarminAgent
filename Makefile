# Makefile for Garmin Agent
# Supports both macOS and Windows (Git Bash)

.PHONY: setup install run test clean

# Detect platform
ifeq ($(OS),Windows_NT)
    PLATFORM := windows
    SHELL := cmd.exe
    SHELLFLAGS := /c
else
    PLATFORM := unix
    SHELL := /bin/bash
endif

VENV_DIR := venv
PYTHON := $(VENV_DIR)/Scripts/python$(if $(findstring windows,$(PLATFORM)),.exe,)
PIP := $(VENV_DIR)/Scripts/pip$(if $(findstring windows,$(PLATFORM)),.exe,)

# Setup virtual environment
setup:
ifneq ("$(wildcard $(PYTHON)*)", "")
	@echo "Virtual environment already exists at $(VENV_DIR)/"
else
	@echo "Creating virtual environment..."
	python -m venv $(VENV_DIR)
endif
	@echo "Upgrading pip..."
	$(PIP) install --upgrade pip

# Install dependencies
install: setup
	@echo "Installing dependencies..."
	$(PIP) install -r requirements.txt
	@echo ""
	@echo "✅ Installation complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Copy .env.example to .env and fill in your credentials"
	@echo "  2. Run: make run (or python main.py)"

# Run the agent
run:
	$(PYTHON) main.py

# Run the CLI
cli:
	$(PYTHON) scripts/garmin_cli.py $(COMMAND)

# Quick test (just import check)
test-import:
	$(PYTHON) -c "from garmin_agent.agent import GarminAgent; print('✅ Import OK')"

# Clean
clean:
	@if [ -d "$(VENV_DIR)" ]; then rm -rf "$(VENV_DIR)"; echo "Removed $(VENV_DIR)/"; fi
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleaned up."

# Show help
help:
	@echo "Garmin Agent Makefile"
	@echo "====================="
	@echo ""
	@echo "Commands:"
	@echo "  make setup     - Create virtual environment"
	@echo "  make install   - Setup + install dependencies"
	@echo "  make run       - Run the interactive agent"
	@echo "  make cli COMMAND=xxx - Run CLI command"
	@echo "  make test-import - Verify imports work"
	@echo "  make clean     - Remove venv and __pycache__"
	@echo "  make help      - Show this help"