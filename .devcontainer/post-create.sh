#!/bin/bash
set -e

echo "=== Span Panel Dev Container Setup ==="

# Navigate to project directory
cd /workspaces/span

# Check if sibling span-panel-api exists
if [ ! -d "/workspaces/span-panel-api" ]; then
    echo ""
    echo "⚠️  WARNING: sibling directory 'span-panel-api' not found at /workspaces/span-panel-api"
    echo "   The pyproject.toml references this as a local dependency."
    echo "   Please ensure span-panel-api is cloned alongside this project:"
    echo ""
    echo "   cd /workspaces"
    echo "   git clone <span-panel-api-repo-url>"
    echo ""
    echo "   Then run 'poetry install' manually."
    echo ""
else
    echo "✓ Found sibling span-panel-api directory"
fi

# Install Python dependencies with Poetry
echo ""
echo "Installing Python dependencies..."
poetry install --no-interaction

# Install pre-commit hooks
echo ""
echo "Setting up pre-commit hooks..."
poetry run pre-commit install

# Verify installation
echo ""
echo "=== Setup Complete ==="
echo ""
echo "Python: $(python --version)"
echo "Poetry: $(poetry --version)"
echo "Virtual env: $(poetry env info --path)"
echo ""
echo "Available commands:"
echo "  poetry run pytest           - Run tests"
echo "  poetry run pre-commit run   - Run all pre-commit hooks"
echo "  poetry run ruff check .     - Run linter"
echo "  poetry run mypy .           - Run type checker"
echo ""
