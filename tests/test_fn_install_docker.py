import unittest
from unittest.mock import patch, call, MagicMock
import subprocess
import os
import sys

# Ensure the parent directory is in the sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)

from utils.fn_install_docker import main, is_docker_installed, install_docker_linux, install_docker_windows, install_docker_macos

class TestFnInstallDocker(unittest.TestCase):

    @patch('utils.fn_install_docker.detect_os')
    @patch('utils.fn_install_docker.detect_architecture')
    @patch('utils.fn_install_docker.subprocess.run')
    def test_is_docker_installed(self, mock_run, mock_detect_architecture, mock_detect_os):
        mock_run.side_effect = subprocess.CalledProcessError(1, 'docker')
        mock_detect_os.return_value = {"os_type": "linux"}
        mock_detect_architecture.return_value = {"dkarch": "amd64"}

        m4b_config = {"system": {"sleep_time": 1}}
        result = is_docker_installed(m4b_config)
        self.assertFalse(result)

        mock_run.side_effect = None
        mock_run.return_value = subprocess.CompletedProcess(args=['docker', '--version'], returncode=0)
        result = is_docker_installed(m4b_config)
        self.assertTrue(result)

    @patch('utils.fn_install_docker.download_file')
    @patch('utils.fn_install_docker.subprocess.run')
    @patch('utils.fn_install_docker.os.remove')
    def test_install_docker_linux(self, mock_remove, mock_run, mock_download_file):
        files_path = '/fake/path'
        mock_run.return_value = subprocess.CompletedProcess(args=['sudo', 'sh', 'get-docker.sh'], returncode=0)

        install_docker_linux(files_path)

        mock_download_file.assert_called_once_with('https://get.docker.com', os.path.join(files_path, 'get-docker.sh'))
        mock_run.assert_has_calls([
            call(['sudo', 'sh', os.path.join(files_path, 'get-docker.sh')], check=True)
        ])
        mock_remove.assert_called_once_with(os.path.join(files_path, 'get-docker.sh'))

    @patch('utils.fn_install_docker.download_file')
    @patch('utils.fn_install_docker.subprocess.run')
    @patch('utils.fn_install_docker.os.remove')
    @patch('utils.fn_install_docker.os.getenv', return_value='C:\\Program Files')
    def test_install_docker_windows(self, mock_getenv, mock_remove, mock_run, mock_download_file):
        files_path = '/fake/path'

        # Mock subprocess.run to simulate a successful installation and launch of Docker Desktop
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0),  # For installation
            subprocess.CompletedProcess(args=[], returncode=0)   # For launching Docker Desktop
        ]

        # Call the function to install Docker on Windows
        install_docker_windows(files_path)

        # Assert that the download_file function was called with the correct arguments
        mock_download_file.assert_called_once_with('https://desktop.docker.com/win/stable/Docker%20Desktop%20Installer.exe', os.path.join(files_path, 'DockerInstaller.exe'))

        # Assert that subprocess.run was called with the correct arguments to install Docker
        mock_run.assert_any_call(
            [os.path.join(files_path, 'DockerInstaller.exe'), 'install', '--accept-license', '--quiet'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            shell=True,
            check=True
        )

        # Assert that subprocess.run was called with the correct arguments to launch Docker Desktop
        mock_run.assert_any_call(
            [os.path.join(os.getenv("ProgramFiles"), "Docker", "Docker", "Docker Desktop.exe")],
            shell=True
        )

        # Assert that the installer executable was removed after installation
        mock_remove.assert_called_once_with(os.path.join(files_path, 'DockerInstaller.exe'))



    @patch('utils.fn_install_docker.download_file')
    @patch('utils.fn_install_docker.subprocess.run')
    def test_install_docker_macos(self, mock_run, mock_download_file):
        files_path = '/fake/path'
        mock_run.return_value = subprocess.CompletedProcess(args=['sudo', 'install', '--accept-license'], returncode=0)

        install_docker_macos(files_path, intel_cpu=True)

        mock_download_file.assert_called_once_with('https://desktop.docker.com/mac/main/amd64/Docker.dmg', os.path.join(files_path, 'Docker.dmg'))
        mock_run.assert_has_calls([
            call(['hdiutil', 'attach', os.path.join(files_path, 'Docker.dmg')], check=True),
            call(['sudo', '/Volumes/Docker/Docker.app/Contents/MacOS/install', '--accept-license'], check=True),
            call(['hdiutil', 'detach', '/Volumes/Docker'], check=True),
            call(['open', '/Applications/Docker.app'], check=True)
        ])

    @patch('utils.fn_install_docker.detect_os')
    @patch('utils.fn_install_docker.detect_architecture')
    @patch('utils.fn_install_docker.install_docker_linux')
    @patch('utils.fn_install_docker.install_docker_windows')
    @patch('utils.fn_install_docker.install_docker_macos')
    def test_main(self, mock_install_macos, mock_install_windows, mock_install_linux, mock_detect_architecture, mock_detect_os):
        mock_detect_os.return_value = {"os_type": "linux"}
        mock_detect_architecture.return_value = {"dkarch": "amd64"}

        app_config = {}
        m4b_config = {"files_path": "/fake/path"}
        user_config = {}

        with patch('builtins.input', return_value='y'):
            main(app_config, m4b_config, user_config)

        mock_install_linux.assert_called_once_with("/fake/path")

        mock_detect_os.return_value = {"os_type": "windows"}
        with patch('builtins.input', return_value='y'):
            main(app_config, m4b_config, user_config)

        mock_install_windows.assert_called_once_with("/fake/path")

        mock_detect_os.return_value = {"os_type": "darwin"}
        mock_detect_architecture.return_value = {"dkarch": "amd64"}
        with patch('builtins.input', return_value='y'):
            main(app_config, m4b_config, user_config)

        mock_install_macos.assert_called_once_with("/fake/path", intel_cpu=True)

if __name__ == '__main__':
    unittest.main()
