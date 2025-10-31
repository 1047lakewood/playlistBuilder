import os
import shutil
import logging
import threading
from datetime import datetime
from typing import Callable, List, Optional
from pathlib import Path


class MigrationUtils:
    """Utilities for migrating configurations and deploying between Active and Stable folders."""

    # Files/folders to exclude during deployment
    DEPLOY_EXCLUDES = {
        '.git',
        '.venv',
        '__pycache__',
        '.pytest_cache',
        '.mypy_cache',
        '.vscode',
        '.idea',
        '.DS_Store',
        'node_modules',
        '*.pyc',
        '*.pyo',
        '*.log',
        'messages_backup_*.json',
        'REAL_REPORT_*.csv',
        'REAL_REPORT_*.pdf',
        'ad_play_statistics_*.json'
    }

    @staticmethod
    def get_default_stable_path(active_root: str) -> str:
        """Get default stable path as sibling with ' - stable' suffix."""
        return os.path.join(os.path.dirname(active_root), os.path.basename(active_root) + " - stable")

    @staticmethod
    def validate_paths(active_root: str, stable_path: str) -> Optional[str]:
        """
        Validate that paths are safe for migration operations.

        Returns None if valid, error message if invalid.
        """
        active_path = Path(active_root).resolve()
        stable_path = Path(stable_path).resolve()

        # Don't allow same paths
        if active_path == stable_path:
            return "Active and Stable paths cannot be the same."

        # Don't allow Stable inside Active or Active inside Stable
        try:
            active_path.relative_to(stable_path)
            return "Active folder cannot be inside Stable folder."
        except ValueError:
            pass

        try:
            stable_path.relative_to(active_path)
            return "Stable folder cannot be inside Active folder."
        except ValueError:
            pass

        return None

    @staticmethod
    def copy_config_file(source_path: str, dest_path: str, backup: bool = True) -> bool:
        """
        Copy config.json from source to dest, optionally backing up dest first.

        Returns True on success.
        """
        config_file = 'config.json'
        source_config = os.path.join(source_path, config_file)
        dest_config = os.path.join(dest_path, config_file)

        try:
            if not os.path.exists(source_config):
                logging.error(f"Source config not found: {source_config}")
                return False

            # Backup destination if it exists and backup requested
            if backup and os.path.exists(dest_config):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_file = os.path.join(dest_path, f"config_backup_{timestamp}.json")
                shutil.copy2(dest_config, backup_file)
                logging.info(f"Backed up existing config to: {backup_file}")

            # Copy the config
            shutil.copy2(source_config, dest_config)
            logging.info(f"Copied config from {source_config} to {dest_config}")
            return True

        except Exception as e:
            logging.exception(f"Failed to copy config from {source_config} to {dest_config}")
            return False

    @staticmethod
    def _should_exclude(path: str, excludes: set) -> bool:
        """Check if a path should be excluded from deployment."""
        name = os.path.basename(path)

        # Check exact matches
        if name in excludes:
            return True

        # Check patterns
        for exclude in excludes:
            if '*' in exclude:
                import fnmatch
                if fnmatch.fnmatch(name, exclude):
                    return True

        return False

    @staticmethod
    def deploy_active_to_stable(active_root: str, stable_path: str, progress_callback: Optional[Callable] = None) -> bool:
        """
        Deploy entire Active folder to Stable (wipe Stable first).

        Excludes common development/artifacts.
        Returns True on success.
        """
        try:
            active_path = Path(active_root)
            stable_path = Path(stable_path)

            # Remove existing stable if it exists
            if stable_path.exists():
                logging.info(f"Removing existing stable folder: {stable_path}")
                # First try to remove .git directory specifically to avoid permission issues
                git_path = stable_path / '.git'
                if git_path.exists():
                    try:
                        shutil.rmtree(git_path)
                        logging.info(f"Removed .git directory from stable folder")
                    except Exception as e:
                        logging.warning(f"Could not remove .git directory: {e}")

                # Now try to remove the rest of the stable folder
                try:
                    shutil.rmtree(stable_path)
                except Exception as e:
                    logging.warning(f"Could not fully remove stable folder, some files may be locked: {e}")
                    # Continue anyway - we'll overwrite files during copy

            # Create fresh stable directory (this will work even if some files remain)
            stable_path.mkdir(parents=True, exist_ok=True)
            logging.info(f"Created/ensured stable folder exists: {stable_path}")

            # Copy all files/folders from active to stable, excluding specified items
            total_items = sum(1 for _ in active_path.rglob('*') if _.is_file() or _.is_dir())
            processed = 0

            for item in active_path.rglob('*'):
                if MigrationUtils._should_exclude(str(item), MigrationUtils.DEPLOY_EXCLUDES):
                    continue

                # Skip .git directory entirely - don't try to copy it
                if '.git' in str(item):
                    continue

                # Calculate relative path
                rel_path = item.relative_to(active_path)
                dest_path = stable_path / rel_path

                try:
                    if item.is_file():
                        # Ensure parent directory exists
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        # Copy with metadata preservation
                        shutil.copy2(item, dest_path)
                    elif item.is_dir():
                        # Create directory
                        dest_path.mkdir(parents=True, exist_ok=True)

                    processed += 1
                    if progress_callback and processed % 10 == 0:  # Update every 10 items
                        progress_callback(f"Copied {processed}/{total_items} items...")

                except Exception as e:
                    logging.warning(f"Failed to copy {item} -> {dest_path}: {e}")
                    continue

            if progress_callback:
                progress_callback("Deployment complete!")

            logging.info(f"Successfully deployed {processed} items to {stable_path}")
            return True

        except Exception as e:
            logging.exception(f"Failed to deploy active to stable: {active_root} -> {stable_path}")
            return False

    @staticmethod
    def run_in_thread(func: Callable, *args, **kwargs) -> threading.Thread:
        """Run a function in a background thread."""
        thread = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=True)
        thread.start()
        return thread
