#!/bin/bash
# Wrapper script to run Chainlit UI debugger from Claude Code

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Get test category from first argument
TEST_CATEGORY="${1:-all}"

# Run the Python test script
python3 test_chainlit_ui.py "$TEST_CATEGORY"
