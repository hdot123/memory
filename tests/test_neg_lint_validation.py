"""Negative test: intentional ruff F401 violation for CI validation."""

import os
import json
import sys  # noqa: F401 -- this will NOT suppress because noqa only works inline per line

# Actually let's make it clean: one unused import that triggers F401
import collections  # F401: unused import


def test_lint_placeholder():
    """Placeholder test to ensure this file is collected."""
    assert True
