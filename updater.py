"""
ezText Auto-Updater

IMPORTANT: This updater is for PORTABLE VERSION ONLY.

For Setup/Installer version:
- Updates are handled directly by ezText.py
- Downloads installer and runs it in normal mode (shows installation wizard)
- Installer handles closing the app and updating files automatically
- Does NOT use this updater.py

For Portable version:
- Would use this updater to replace files after download
- Currently ezText only supports Setup version

Update Process (Setup version):
1. Auto-check on startup
2. Auto-download if update available
3. Show installer wizard to user
4. Installer closes app automatically (via setup.iss)
5. User completes installation
"""

import sys
import os
import json
import urllib.request
import urllib.error
import subprocess
import tempfile
from pathlib import Path
from packaging import version


class AutoUpdater:
    def __init__(self, current_version, repo_owner, repo_name):
        """
        Initialize AutoUpdater

        Args:
            current_version: Current application version (e.g., "1.0.0")
            repo_owner: GitHub repository owner
            repo_name: GitHub repository name
        """
        self.current_version = current_version
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"

    def check_for_updates(self):
        """
        Check if a new version is available

        Returns:
            tuple: (bool, dict) - (update_available, release_info)
        """
        try:
            request = urllib.request.Request(self.api_url)
            request.add_header('User-Agent', 'ezText-AutoUpdater')

            with urllib.request.urlopen(request, timeout=10) as response:
                data = json.loads(response.read().decode())

                latest_version = data['tag_name'].lstrip('v')

                # Compare versions
                if version.parse(latest_version) > version.parse(self.current_version):
                    return True, {
                        'version': latest_version,
                        'download_url': self._get_installer_url(data),
                        'release_notes': data.get('body', ''),
                        'html_url': data.get('html_url', '')
                    }
                else:
                    return False, None

        except urllib.error.URLError as e:
            print(f"Network error checking for updates: {e}")
            return False, None
        except Exception as e:
            print(f"Error checking for updates: {e}")
            return False, None

    def _get_installer_url(self, release_data):
        """
        Get the installer download URL from release assets

        Args:
            release_data: GitHub release API response

        Returns:
            str: Download URL for the installer
        """
        assets = release_data.get('assets', [])

        # Look for the setup executable (case-insensitive)
        for asset in assets:
            name = asset['name'].lower()
            # Match any of these patterns:
            # - ezText_Setup.exe
            # - eztext_setup.exe (case insensitive)
            # - Any .exe file containing 'setup'
            if 'setup' in name and name.endswith('.exe'):
                return asset['browser_download_url']

        return None

    def download_and_install(self, download_url, silent=False):
        """
        Download and install the update (LEGACY - NOT USED)

        NOTE: This function is kept for backward compatibility but is no longer used.
        Setup version updates are now handled directly by ezText.py without using updater.

        For setup version updates, ezText.py:
        1. Auto-checks for updates on startup
        2. Downloads installer directly if update available
        3. Runs installer in normal mode (no silent flags) - shows wizard to user
        4. Installer closes the app automatically via setup.iss code
        5. User completes installation through wizard
        6. Installer updates all files

        Args:
            download_url: URL to download the installer
            silent: Whether to run installer silently

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create temp directory
            temp_dir = tempfile.gettempdir()
            installer_path = os.path.join(temp_dir, 'ezText_Setup.exe')

            # Download the installer
            print(f"Downloading update from {download_url}...")
            urllib.request.urlretrieve(download_url, installer_path)

            # Run the installer
            print(f"Running installer: {installer_path}")
            if silent:
                subprocess.Popen([installer_path, '/VERYSILENT', '/NORESTART'])
            else:
                subprocess.Popen([installer_path])

            # Exit current application to allow update
            return True

        except Exception as e:
            print(f"Error downloading/installing update: {e}")
            return False

    def get_version_info(self):
        """
        Get current version information

        Returns:
            str: Current version
        """
        return self.current_version
