#!/usr/bin/env python3
"""Quick test script for migration utilities."""

import os
import tempfile
import json
from pathlib import Path
from src.migration_utils import MigrationUtils

def test_migration_utils():
    """Test the migration utility functions."""

    # Create temporary directories
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        active_dir = temp_path / "active"
        stable_dir = temp_path / "stable"

        active_dir.mkdir()
        stable_dir.mkdir()

        # Create test config files
        active_config = {"test": "active_value"}
        stable_config = {"test": "stable_value"}

        with open(active_dir / "config.json", 'w') as f:
            json.dump(active_config, f)

        with open(stable_dir / "config.json", 'w') as f:
            json.dump(stable_config, f)

        print("[OK] Created test directories and config files")

        # Test path validation
        error = MigrationUtils.validate_paths(str(active_dir), str(stable_dir))
        assert error is None, f"Path validation failed: {error}"
        print("[OK] Path validation passed")

        # Test invalid paths
        error = MigrationUtils.validate_paths(str(active_dir), str(active_dir))
        assert error is not None, "Should reject same paths"
        print("[OK] Same path rejection works")

        # Test config copy
        success = MigrationUtils.copy_config_file(str(stable_dir), str(active_dir), backup=True)
        assert success, "Config copy failed"
        print("[OK] Config copy works")

        # Verify backup was created
        backup_files = list(active_dir.glob("config_backup_*.json"))
        assert len(backup_files) == 1, "Backup not created"
        print("[OK] Backup creation works")

        # Test deployment
        success = MigrationUtils.deploy_active_to_stable(str(active_dir), str(stable_dir))
        assert success, "Deployment failed"
        print("[OK] Deployment works")

        print("\n[SUCCESS] All migration utility tests passed!")

if __name__ == "__main__":
    test_migration_utils()
