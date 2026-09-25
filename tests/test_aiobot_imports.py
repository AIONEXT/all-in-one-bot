#!/usr/bin/env python3
"""
Pytest tests for AIO Bot.
"""

import sys
from pathlib import Path

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_all_imports():
    """Test that all AIO Bot modules can be imported."""
    import test_imports as ti
    result = ti.main()
    assert result == 0, "Some modules failed to import"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
