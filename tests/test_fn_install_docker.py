"""Tests for the Docker Setup module (fn_install_docker)."""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from money4band.fn_install_docker import (
    _AUTO_INSTALLERS,
    _INSTALL_GUIDES,
    _has_tool,
    is_docker_installed,
    main,
    show_docker_guide,
)


# ---------------------------------------------------------------------------
# is_docker_installed
# ---------------------------------------------------------------------------


@patch("money4band.fn_install_docker._docker_responds", return_value=True)
@patch("money4band.fn_install_docker.shutil.which", return_value="/usr/bin/docker")
def test_is_docker_installed_true(mock_which, mock_responds):
    assert is_docker_installed() is True


@patch("money4band.fn_install_docker.shutil.which", return_value=None)
def test_is_docker_installed_no_binary(mock_which):
    assert is_docker_installed() is False


@patch("money4band.fn_install_docker._docker_responds", return_value=False)
@patch("money4band.fn_install_docker.shutil.which", return_value="/usr/bin/docker")
def test_is_docker_installed_daemon_down(mock_which, mock_responds):
    assert is_docker_installed() is False


# ---------------------------------------------------------------------------
# _has_tool
# ---------------------------------------------------------------------------


@patch("money4band.fn_install_docker.shutil.which", return_value="/usr/bin/curl")
def test_has_tool_found(mock_which):
    assert _has_tool("curl") is True


@patch("money4band.fn_install_docker.shutil.which", return_value=None)
def test_has_tool_missing(mock_which):
    assert _has_tool("curl") is False


# ---------------------------------------------------------------------------
# show_docker_guide
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("os_key", ["linux", "windows", "darwin"])
@patch("money4band.fn_install_docker.platform.system")
def test_show_docker_guide_known_os(mock_system, os_key, capsys):
    mock_system.return_value = os_key.capitalize() if os_key != "darwin" else "Darwin"
    show_docker_guide()
    out = capsys.readouterr().out
    assert "docker" in out.lower() or "Docker" in out


@patch("money4band.fn_install_docker.platform.system", return_value="FreeBSD")
def test_show_docker_guide_unknown_os(mock_system, capsys):
    show_docker_guide()
    out = capsys.readouterr().out
    assert "Unsupported OS" in out


# ---------------------------------------------------------------------------
# main — already installed
# ---------------------------------------------------------------------------


@patch("builtins.input")
@patch("money4band.fn_install_docker.is_docker_installed", return_value=True)
@patch("money4band.fn_install_docker.subprocess.run")
@patch("money4band.fn_install_docker.cls")
def test_main_docker_already_installed(mock_cls, mock_run, mock_installed, mock_input, capsys):
    mock_run.return_value = type("R", (), {"returncode": 0, "stdout": "Docker version 27.0.0"})()
    main("a", "b", "c")
    out = capsys.readouterr().out
    assert "already installed" in out


# ---------------------------------------------------------------------------
# main — auto-install offered and accepted
# ---------------------------------------------------------------------------


@patch("builtins.input")
@patch("money4band.fn_install_docker.show_docker_guide")
@patch("money4band.fn_install_docker.ask_question_yn", return_value=True)
@patch("money4band.fn_install_docker._has_tool", return_value=True)
@patch("money4band.fn_install_docker.platform.system", return_value="Linux")
@patch("money4band.fn_install_docker.is_docker_installed", return_value=False)
@patch("money4band.fn_install_docker.cls")
def test_main_auto_install_accepted_success(
    mock_cls, mock_installed, mock_system, mock_has_tool, mock_yn, mock_guide, mock_input, capsys
):
    mock_installer = MagicMock(return_value=True)
    with patch.dict(
        "money4band.fn_install_docker._AUTO_INSTALLERS",
        {"linux": ("curl", mock_installer, "test cmd")},
    ):
        main("a", "b", "c")
        mock_installer.assert_called_once()
    # Guide should NOT be shown when auto-install succeeds
    mock_guide.assert_not_called()


@patch("builtins.input")
@patch("money4band.fn_install_docker.show_docker_guide")
@patch("money4band.fn_install_docker.ask_question_yn", return_value=True)
@patch("money4band.fn_install_docker._has_tool", return_value=True)
@patch("money4band.fn_install_docker.platform.system", return_value="Linux")
@patch("money4band.fn_install_docker.is_docker_installed", return_value=False)
@patch("money4band.fn_install_docker.cls")
def test_main_auto_install_accepted_fails_shows_guide(
    mock_cls, mock_installed, mock_system, mock_has_tool, mock_yn, mock_guide, mock_input, capsys
):
    mock_installer = MagicMock(return_value=False)
    with patch.dict(
        "money4band.fn_install_docker._AUTO_INSTALLERS",
        {"linux": ("curl", mock_installer, "test cmd")},
    ):
        main("a", "b", "c")
    # Installer failed → guide shown as fallback
    mock_guide.assert_called_once()


# ---------------------------------------------------------------------------
# main — auto-install offered but declined
# ---------------------------------------------------------------------------


@patch("builtins.input")
@patch("money4band.fn_install_docker.show_docker_guide")
@patch("money4band.fn_install_docker.ask_question_yn", return_value=False)
@patch("money4band.fn_install_docker._has_tool", return_value=True)
@patch("money4band.fn_install_docker.platform.system", return_value="Windows")
@patch("money4band.fn_install_docker.is_docker_installed", return_value=False)
@patch("money4band.fn_install_docker.cls")
def test_main_auto_install_declined_shows_guide(
    mock_cls, mock_installed, mock_system, mock_has_tool, mock_yn, mock_guide, mock_input, capsys
):
    main("a", "b", "c")
    mock_guide.assert_called_once()


# ---------------------------------------------------------------------------
# main — tool not available, straight to guide
# ---------------------------------------------------------------------------


@patch("builtins.input")
@patch("money4band.fn_install_docker.show_docker_guide")
@patch("money4band.fn_install_docker._has_tool", return_value=False)
@patch("money4band.fn_install_docker.platform.system", return_value="Darwin")
@patch("money4band.fn_install_docker.is_docker_installed", return_value=False)
@patch("money4band.fn_install_docker.cls")
def test_main_no_tool_shows_guide(mock_cls, mock_installed, mock_system, mock_has_tool, mock_guide, mock_input, capsys):
    main("a", "b", "c")
    mock_guide.assert_called_once()


# ---------------------------------------------------------------------------
# Guide content sanity
# ---------------------------------------------------------------------------
# Guide content sanity
# ---------------------------------------------------------------------------


def test_install_guides_have_all_platforms():
    assert set(_INSTALL_GUIDES.keys()) == {"linux", "windows", "darwin"}


@pytest.mark.parametrize("os_key", ["linux", "windows", "darwin"])
def test_guide_contains_url(os_key):
    assert "https://" in _INSTALL_GUIDES[os_key]
