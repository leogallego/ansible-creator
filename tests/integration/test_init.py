"""Unit tests for ansible-creator init."""

from __future__ import annotations

import re

from typing import TYPE_CHECKING

import pytest

from tests.defaults import CREATOR_BIN


if TYPE_CHECKING:
    from pathlib import Path

    from tests.conftest import CliRunCallable


def test_run_help(cli: CliRunCallable) -> None:
    """Test running ansible-creator --help.

    Args:
        cli: cli_run function.
    """
    # Get the path to the current python interpreter
    result = cli(f"{CREATOR_BIN} --help", env={"NO_COLOR": "1"})
    assert result.returncode == 0, (result.stdout, result.stderr)

    assert "The fastest way to generate all your ansible content." in result.stdout
    assert re.search(r"positional arguments:", result.stdout, re.IGNORECASE)
    assert "add" in result.stdout
    assert "Add resources to an existing Ansible project." in result.stdout
    assert "init" in result.stdout
    assert "Initialize a new Ansible project." in result.stdout


def test_run_no_subcommand(cli: CliRunCallable) -> None:
    """Test running ansible-creator without subcommand.

    Args:
        cli: cli_run function.
    """
    result = cli(str(CREATOR_BIN))
    assert result.returncode != 0
    assert "the following arguments are required: command" in result.stderr


@pytest.mark.parametrize(
    argnames="command",
    argvalues=("init --project ansible-project", "init --init-path /tmp"),
    ids=["project_no_scm", "collection_no_name"],
)
def test_run_deprecated_failure(command: str, cli: CliRunCallable) -> None:
    """Test running ansible-creator init with deprecated options.

    Args:
        command: Command to run.
        cli: cli_run function.
    """
    result = cli(f"{CREATOR_BIN} {command}")
    assert result.returncode != 0
    assert "is no longer needed and will be removed." in result.stdout
    assert "The CLI has changed." in result.stderr


@pytest.mark.parametrize(
    argnames=("args", "expected"),
    argvalues=(
        ("a.b", "must be longer than 2 characters."),
        ("_a.b", "cannot begin with an underscore."),
        ("foo", "must be in the format '<namespace>.<name>'."),
    ),
    ids=("short", "underscore", "no_dot"),
)
@pytest.mark.parametrize("command", ("collection", "playbook"))
def test_run_init_invalid_name(command: str, args: str, expected: str, cli: CliRunCallable) -> None:
    """Test running ansible-creator init with invalid collection name.

    Args:
        command: Command to run.
        args: Arguments to pass to the CLI.
        expected: Expected error message.
        cli: cli_run function.
    """
    result = cli(f"{CREATOR_BIN} init {command} {args}")
    assert result.returncode != 0
    assert result.stderr.startswith("Critical:")
    assert expected in result.stderr


def test_run_init_basic(cli: CliRunCallable, tmp_path: Path) -> None:
    """Test running ansible-creator init with empty/non-empty/force.

    Args:
        cli: cli_run function.
        tmp_path: Temporary path.
    """
    final_dest = f"{tmp_path}/collections/ansible_collections"
    cli(f"mkdir -p {final_dest}")

    result = cli(
        f"{CREATOR_BIN} init testorg.testcol --init-path {final_dest}",
    )
    assert result.returncode == 0

    # check stdout
    assert r"Note: collection project created at" in result.stdout

    # fail to override existing collection with force=false (default)
    result = cli(
        f"{CREATOR_BIN} init testorg.testcol --init-path {final_dest}",
    )

    assert result.returncode != 0

    # override existing collection with force=true
    result = cli(f"{CREATOR_BIN} init testorg.testcol --init-path {tmp_path} --force")
    assert result.returncode == 0
    assert r"Warning: re-initializing existing directory" in result.stdout

    # override existing collection with override=true
    result = cli(f"{CREATOR_BIN} init testorg.testcol --init-path {tmp_path} --overwrite")
    assert result.returncode == 0
    assert re.search(f"Note: collection project created at {tmp_path}", result.stdout) is not None

    # use no-override=true
    result = cli(f"{CREATOR_BIN} init testorg.testcol --init-path {tmp_path} --no-overwrite")
    assert result.returncode != 0
    assert re.search(r"The flag `--no-overwrite` restricts overwriting.", result.stderr) is not None


def test_run_init_minimal_collection(
    cli: CliRunCallable,
    tmp_path: Path,
) -> None:
    """Test ansible-creator init collection with --minimal flag.

    Args:
        cli: The cli fixture.
        tmp_path: Temporary directory path.
    """
    result = cli(
        f"{CREATOR_BIN} init collection testns.testcol"
        f" {tmp_path} --minimal",
    )
    assert result.returncode == 0
    assert "Note: collection project created" in result.stdout

    # Essential files must exist
    assert (tmp_path / "galaxy.yml").exists()
    assert (tmp_path / "README.md").exists()
    assert (tmp_path / "meta" / "runtime.yml").exists()
    assert (tmp_path / "plugins" / "modules" / "__init__.py").exists()
    assert (tmp_path / ".gitignore").exists()

    # Non-essential files must NOT exist
    assert not (tmp_path / ".devcontainer").exists()
    assert not (tmp_path / ".vscode").exists()
    assert not (tmp_path / "devfile.yaml").exists()
    assert not (tmp_path / "roles").exists()
    assert not (tmp_path / "extensions").exists()
    assert not (tmp_path / ".github").exists()
    assert not (tmp_path / "pyproject.toml").exists()
    assert not (tmp_path / "CODE_OF_CONDUCT.md").exists()
    assert not (tmp_path / "plugins" / "action" / "sample_action.py").exists()
    assert not (tmp_path / "plugins" / "filter" / "sample_filter.py").exists()


def test_run_init_minimal_playbook(
    cli: CliRunCallable,
    tmp_path: Path,
) -> None:
    """Test ansible-creator init playbook with --minimal flag.

    Args:
        cli: The cli fixture.
        tmp_path: Temporary directory path.
    """
    result = cli(
        f"{CREATOR_BIN} init playbook testns.testcol"
        f" {tmp_path} --minimal",
    )
    assert result.returncode == 0
    assert "Note: playbook project created" in result.stdout

    # Essential files must exist
    assert (tmp_path / "site.yml").exists()
    assert (tmp_path / "ansible.cfg").exists()
    assert (tmp_path / "inventory" / "hosts.yml").exists()
    assert (tmp_path / "collections" / "requirements.yml").exists()
    assert (tmp_path / ".gitignore").exists()

    # Non-essential files must NOT exist
    assert not (tmp_path / ".devcontainer").exists()
    assert not (tmp_path / ".vscode").exists()
    assert not (tmp_path / "devfile.yaml").exists()
    assert not (tmp_path / "linux_playbook.yml").exists()
    assert not (tmp_path / "network_playbook.yml").exists()
    assert not (tmp_path / ".github").exists()
    assert not (tmp_path / "collections" / "ansible_collections").exists()
    assert not (tmp_path / "inventory" / "host_vars").exists()
    assert not (tmp_path / "argspec_validation_plays.yml").exists()


def test_run_init_ee(cli: CliRunCallable, tmp_path: Path) -> None:
    """Test running ansible-creator init for ee_project.

    Args:
        cli: cli_run function.
        tmp_path: Temporary path.
    """
    final_dest = f"{tmp_path}/ee_project"
    cli(f"mkdir -p {final_dest}")

    result = cli(
        f"{CREATOR_BIN} init execution_env {final_dest}",
    )
    assert result.returncode == 0

    # check stdout
    assert r"Note: execution_env project created at" in result.stdout
