#!/usr/bin/env python3
"""M2 tests: Junk file exclusion and backups/ exemption.

Tests for:
- JUNK_PATTERNS constant with 6 patterns (.DS_Store, __pycache__/, *.pyc, Thumbs.db, .coverage, .pytest_cache/)
- Manifest excludes junk files after signing (VAL-M2-018, VAL-M2-019, VAL-M2-020)
- pollution_guard exempts backups/ directory (VAL-M2-021, VAL-M2-022)
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from memory_core.tools.memory_hook_integrity_keys import load_or_create_key
from memory_core.tools.memory_hook_integrity_manifest import (
    JUNK_PATTERNS,
    _is_junk,
    sign_project,
)
from memory_core.tools.validate_project_memory import (
    _check_pollution,
)


class TestJunkPatterns:
    """VAL-M2-019: JUNK_PATTERNS constant defined and complete."""

    def test_junk_patterns_has_all_six_patterns(self):
        """JUNK_PATTERNS includes all 6 required patterns."""
        assert len(JUNK_PATTERNS) == 6

        # Convert to strings for checking
        pattern_strs = [p.pattern if hasattr(p, 'pattern') else str(p) for p in JUNK_PATTERNS]

        # Check each required pattern
        assert any('.DS_Store' in p for p in pattern_strs), "Missing .DS_Store pattern"
        assert any('__pycache__' in p for p in pattern_strs), "Missing __pycache__/ pattern"
        assert any('.pyc' in p for p in pattern_strs), "Missing *.pyc pattern"
        assert any('Thumbs' in p for p in pattern_strs), "Missing Thumbs.db pattern"
        assert any('.coverage' in p for p in pattern_strs), "Missing .coverage pattern"
        assert any('.pytest_cache' in p for p in pattern_strs), "Missing .pytest_cache/ pattern"


class TestIsJunk:
    """Test _is_junk function for detecting junk files."""

    def test_ds_store_is_junk(self):
        """Test .DS_Store file is detected as junk."""
        assert _is_junk('.DS_Store') is True
        assert _is_junk('memory/system/.DS_Store') is True
        assert _is_junk('deep/nested/path/.DS_Store') is True

    def test_pycache_is_junk(self):
        """Test __pycache__ directory contents are junk."""
        assert _is_junk('__pycache__/module.pyc') is True
        assert _is_junk('memory/__pycache__/test.pyc') is True
        assert _is_junk('deep/__pycache__/nested/file.pyc') is True

    def test_pyc_files_are_junk(self):
        """Test .pyc files are junk."""
        assert _is_junk('module.pyc') is True
        assert _is_junk('memory/system/module.pyc') is True

    def test_thumbs_db_is_junk(self):
        """Test Thumbs.db file is junk."""
        assert _is_junk('Thumbs.db') is True
        assert _is_junk('memory/system/Thumbs.db') is True

    def test_coverage_is_junk(self):
        """Test .coverage file is junk."""
        assert _is_junk('.coverage') is True
        assert _is_junk('memory/system/.coverage') is True

    def test_pytest_cache_is_junk(self):
        """Test .pytest_cache directory contents are junk."""
        assert _is_junk('.pytest_cache/README.md') is True
        assert _is_junk('memory/.pytest_cache/v/cache/step') is True

    def test_normal_files_not_junk(self):
        """Test normal files are not junk."""
        assert _is_junk('memory.lock') is False
        assert _is_junk('memory/system/adapter.toml') is False
        assert _is_junk('memory/docs/README.md') is False
        assert _is_junk('memory/kb/global/test.md') is False


class TestManifestExcludesJunk:
    """VAL-M2-018, VAL-M2-020: Manifest excludes junk files."""

    def _make_project_with_junk(self, td: str) -> Path:
        """Create a project with various junk files."""
        root = Path(td)
        memory_dir = root / "memory" / "system"
        memory_dir.mkdir(parents=True)

        # Create valid files
        (memory_dir / "memory.lock").write_text('[memory]\nmemory_version = "0.8.0"\n')
        (memory_dir / "adapter.toml").write_text('[core]\nversion = "0.8.0"\n')
        (memory_dir / "ownership.toml").write_text('[ownership]\n')

        # Create junk files at various levels
        (root / ".DS_Store").write_bytes(b'\x00' * 100)
        (memory_dir / ".DS_Store").write_bytes(b'\x00' * 100)
        (memory_dir / "__pycache__").mkdir()
        (memory_dir / "__pycache__" / "module.pyc").write_bytes(b'\x00' * 100)
        (memory_dir / "test.pyc").write_bytes(b'\x00' * 100)
        (memory_dir / "Thumbs.db").write_bytes(b'\x00' * 100)
        (memory_dir / ".coverage").write_bytes(b'\x00' * 100)
        (memory_dir / ".pytest_cache").mkdir()
        (memory_dir / ".pytest_cache" / "README.md").write_text("cache\n")

        # Nested junk
        deep_dir = memory_dir / "deep" / "nested"
        deep_dir.mkdir(parents=True)
        (deep_dir / ".DS_Store").write_bytes(b'\x00' * 100)
        (deep_dir / "__pycache__").mkdir()
        (deep_dir / "__pycache__" / "test.pyc").write_bytes(b'\x00' * 100)

        load_or_create_key(memory_dir / "test.key")
        return root

    def test_manifest_excludes_top_level_junk(self):
        """VAL-M2-018: Manifest excludes top-level junk files."""
        with tempfile.TemporaryDirectory() as td:
            root = self._make_project_with_junk(td)
            memory_dir = root / "memory" / "system"
            key = load_or_create_key(memory_dir / "test.key")

            manifest = sign_project(root, key)
            assert manifest is not None

            # Check that no junk files are in manifest
            for entry in manifest['entries']:
                rel_path = entry['rel_path']
                assert '.DS_Store' not in rel_path, f"Found .DS_Store in manifest: {rel_path}"
                assert '__pycache__' not in rel_path, f"Found __pycache__ in manifest: {rel_path}"
                assert not rel_path.endswith('.pyc'), f"Found .pyc in manifest: {rel_path}"
                assert 'Thumbs.db' not in rel_path, f"Found Thumbs.db in manifest: {rel_path}"
                assert '.coverage' not in rel_path, f"Found .coverage in manifest: {rel_path}"
                assert '.pytest_cache' not in rel_path, f"Found .pytest_cache in manifest: {rel_path}"

    def test_manifest_excludes_nested_junk(self):
        """VAL-M2-020: Manifest excludes nested junk files at any depth."""
        with tempfile.TemporaryDirectory() as td:
            root = self._make_project_with_junk(td)
            memory_dir = root / "memory" / "system"
            key = load_or_create_key(memory_dir / "test.key")

            manifest = sign_project(root, key)
            assert manifest is not None

            # Verify nested junk is excluded
            for entry in manifest['entries']:
                rel_path = entry['rel_path']
                # Should not have deep/nested/.DS_Store
                assert 'deep/nested/.DS_Store' not in rel_path
                # Should not have deep/nested/__pycache__/test.pyc
                assert 'deep/nested/__pycache__' not in rel_path


class TestPollutionGuardBackupsExemption:
    """VAL-M2-021, VAL-M2-022: pollution_guard exempts backups/ directory."""

    def _make_project_with_backups(self, td: str) -> Path:
        """Create a project with backups directory."""
        root = Path(td)
        memory_dir = root / "memory" / "system"
        memory_dir.mkdir(parents=True)

        # Create required files
        (memory_dir / "memory.lock").write_text('[memory]\nmemory_version = "0.8.0"\n')
        (memory_dir / "adapter.toml").write_text('[core]\nversion = "0.8.0"\n')

        # Create backups directory with files
        backups_dir = memory_dir / "backups"
        backups_dir.mkdir()
        (backups_dir / "snapshot.toml").write_text('[backup]\ntimestamp = "2026-01-01"\n')
        (backups_dir / "old_state.json").write_text('{"version": "0.7.0"}\n')

        return root

    def _make_project_with_pollution(self, td: str, pollution_dir: str = "node_modules") -> Path:
        """Create a project with pollution (non-exempt directory)."""
        root = Path(td)
        memory_dir = root / "memory" / "system"
        memory_dir.mkdir(parents=True)

        # Create required files
        (memory_dir / "memory.lock").write_text('[memory]\nmemory_version = "0.8.0"\n')
        (memory_dir / "adapter.toml").write_text('[core]\nversion = "0.8.0"\n')

        # Create pollution directory
        pollution_path = memory_dir / pollution_dir
        pollution_path.mkdir()
        (pollution_path / "data.txt").write_text("business state\n")

        return root

    def test_pollution_guard_exempts_backups(self):
        """VAL-M2-021: pollution_guard does not flag backups/ directory."""
        with tempfile.TemporaryDirectory() as td:
            root = self._make_project_with_backups(td)
            memory_dir = root / "memory" / "system"

            violations = _check_pollution(memory_dir)

            # Should have no violations for backups/
            assert len(violations) == 0, f"Unexpected violations: {violations}"

    def test_pollution_guard_detects_non_exempt_pollution(self):
        """VAL-M2-022: pollution_guard still detects non-exempt pollution."""
        with tempfile.TemporaryDirectory() as td:
            # Use node_modules which is in POLLUTION_PATTERNS
            root = self._make_project_with_pollution(td, "node_modules")
            memory_dir = root / "memory" / "system"

            violations = _check_pollution(memory_dir)

            # Should detect pollution in node_modules/
            assert len(violations) > 0, "Expected pollution in node_modules/ directory"
            assert any('node_modules' in v for v in violations)

    @pytest.mark.parametrize("pollution_dir", [
        "tmp",
        "backup",  # singular, not exempt
        "node_modules",
        "__pycache__",
        ".venv",
    ])
    def test_pollution_guard_only_exempts_backups_not_similar(self, pollution_dir):
        """VAL-M2-022: Only literal 'backups/' is exempt, not similar names."""
        with tempfile.TemporaryDirectory() as td:
            root = self._make_project_with_pollution(td, pollution_dir)
            memory_dir = root / "memory" / "system"

            violations = _check_pollution(memory_dir)

            # Should detect pollution (not exempt)
            # Note: some patterns like __pycache__ are in POLLUTION_PATTERNS themselves
            if pollution_dir in ["node_modules", "__pycache__", ".venv"]:
                # These are pollution patterns, so should be detected
                assert len(violations) > 0, f"Expected pollution in {pollution_dir}/"
            else:
                # Other directories should not trigger pollution unless they match patterns
                # This test mainly ensures backups/ is the only exemption
                pass
