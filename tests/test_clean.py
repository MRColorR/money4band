"""Tests for ``money4band.docker.clean.clean_orphans``."""

from __future__ import annotations

import json
import subprocess
from unittest.mock import patch

from money4band.docker.clean import CleanResult, clean_orphans


def _proc(stdout: str = "", stderr: str = "", returncode: int = 0):
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=stderr
    )


def _ps_line(name: str, state: str, cid: str | None = None) -> str:
    return json.dumps({"ID": cid or f"id-{name}", "Names": name, "State": state})


class TestCleanOrphans:
    def test_removes_stopped_containers_skips_running(self):
        ps_output = "\n".join([
            _ps_line("alpha", "exited"),
            _ps_line("bravo", "running"),
            _ps_line("charlie", "created"),
        ])

        def fake_run(cmd, *args, **kwargs):
            if cmd[:3] == ["docker", "ps", "-a"]:
                return _proc(stdout=ps_output)
            if cmd[:2] == ["docker", "rm"]:
                return _proc()
            if cmd[:3] == ["docker", "network", "ls"]:
                return _proc()
            if cmd[:3] == ["docker", "network", "inspect"]:
                return _proc(stdout="0\n")
            return _proc()

        with patch("money4band.docker.clean.subprocess.run", side_effect=fake_run):
            result = clean_orphans("m4b-test")

        assert set(result.containers_removed) == {"alpha", "charlie"}
        assert "bravo" not in result.containers_removed
        assert result.errors == []

    def test_dry_run_does_not_call_rm(self):
        ps_output = _ps_line("alpha", "exited")
        rm_calls: list[list[str]] = []

        def fake_run(cmd, *args, **kwargs):
            if cmd[:2] == ["docker", "rm"]:
                rm_calls.append(cmd)
                return _proc()
            if cmd[:3] == ["docker", "ps", "-a"]:
                return _proc(stdout=ps_output)
            if cmd[:3] == ["docker", "network", "ls"]:
                return _proc()
            if cmd[:3] == ["docker", "volume", "ls"]:
                return _proc()
            return _proc()

        with patch("money4band.docker.clean.subprocess.run", side_effect=fake_run):
            result = clean_orphans("m4b-test", dry_run=True)

        assert result.containers_removed == ["alpha"]
        assert rm_calls == []

    def test_volumes_opt_in_default_skipped(self):
        vol_calls: list[list[str]] = []

        def fake_run(cmd, *args, **kwargs):
            if cmd[:3] == ["docker", "ps", "-a"]:
                return _proc()
            if cmd[:3] == ["docker", "network", "ls"]:
                return _proc()
            if cmd[:3] == ["docker", "volume", "ls"]:
                vol_calls.append(cmd)
                return _proc(stdout="m4b-test_data\n")
            return _proc()

        with patch("money4band.docker.clean.subprocess.run", side_effect=fake_run):
            result = clean_orphans("m4b-test", include_volumes=False)

        assert vol_calls == [], "volume listing must be skipped when include_volumes=False"
        assert result.volumes_removed == []

    def test_volumes_removed_when_opt_in(self):
        rm_calls: list[list[str]] = []

        def fake_run(cmd, *args, **kwargs):
            if cmd[:3] == ["docker", "ps", "-a"]:
                return _proc()
            if cmd[:3] == ["docker", "network", "ls"]:
                return _proc()
            if cmd[:3] == ["docker", "volume", "ls"]:
                return _proc(stdout="m4b-test_data\nm4b-test_logs\n")
            if cmd[:3] == ["docker", "volume", "rm"]:
                rm_calls.append(cmd)
                return _proc()
            return _proc()

        with patch("money4band.docker.clean.subprocess.run", side_effect=fake_run):
            result = clean_orphans("m4b-test", include_volumes=True)

        assert set(result.volumes_removed) == {"m4b-test_data", "m4b-test_logs"}
        assert len(rm_calls) == 2

    def test_networks_in_use_are_skipped(self):
        def fake_run(cmd, *args, **kwargs):
            if cmd[:3] == ["docker", "ps", "-a"]:
                return _proc()
            if cmd[:3] == ["docker", "network", "ls"]:
                return _proc(stdout="net-1\tm4b-test_default\nnet-2\tm4b-test_proxy\n")
            if cmd[:3] == ["docker", "network", "inspect"]:
                # net-1 has containers attached, net-2 is unused
                cid = cmd[-1]
                count = "2" if cid == "net-1" else "0"
                return _proc(stdout=f"{count}\n")
            if cmd[:3] == ["docker", "network", "rm"]:
                return _proc()
            return _proc()

        with patch("money4band.docker.clean.subprocess.run", side_effect=fake_run):
            result = clean_orphans("m4b-test")

        assert result.networks_removed == ["m4b-test_proxy"]
        assert "m4b-test_default" not in result.networks_removed

    def test_label_filter_uses_project_name(self):
        captured: list[list[str]] = []

        def fake_run(cmd, *args, **kwargs):
            captured.append(cmd)
            return _proc()

        with patch("money4band.docker.clean.subprocess.run", side_effect=fake_run):
            clean_orphans("my-m4b-project")

        ps_cmd = next(c for c in captured if c[:3] == ["docker", "ps", "-a"])
        assert "label=com.docker.compose.project=my-m4b-project" in ps_cmd
        net_cmd = next(c for c in captured if c[:3] == ["docker", "network", "ls"])
        assert "label=com.docker.compose.project=my-m4b-project" in net_cmd

    def test_docker_failure_recorded_in_errors(self):
        def fake_run(cmd, *args, **kwargs):
            if cmd[:3] == ["docker", "ps", "-a"]:
                return _proc(returncode=1, stderr="Cannot connect to the Docker daemon")
            return _proc()

        with patch("money4band.docker.clean.subprocess.run", side_effect=fake_run):
            result = clean_orphans("m4b-test")

        assert result.containers_removed == []
        assert any("Cannot connect" in e for e in result.errors)

    def test_rm_failure_recorded_per_container(self):
        ps_output = _ps_line("alpha", "exited")

        def fake_run(cmd, *args, **kwargs):
            if cmd[:3] == ["docker", "ps", "-a"]:
                return _proc(stdout=ps_output)
            if cmd[:2] == ["docker", "rm"]:
                return _proc(returncode=1, stderr="permission denied")
            if cmd[:3] == ["docker", "network", "ls"]:
                return _proc()
            return _proc()

        with patch("money4band.docker.clean.subprocess.run", side_effect=fake_run):
            result = clean_orphans("m4b-test")

        assert result.containers_removed == []
        assert any("rm container alpha" in e for e in result.errors)

    def test_total_counts_all_resource_kinds(self):
        result = CleanResult(
            project="x",
            containers_removed=["a", "b"],
            networks_removed=["n1"],
            volumes_removed=["v1", "v2", "v3"],
        )
        assert result.total == 6
