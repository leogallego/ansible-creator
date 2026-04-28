# Design: `--minimal` flag for `init collection` and `init playbook`

## Problem

`ansible-creator init collection` scaffolds 60+ files including sample plugins, stub roles, EDA rulebooks, molecule tests, devcontainer configs, and CI workflows. Experienced users must immediately clean up the noise. Upstream issues [#463](https://github.com/ansible/ansible-creator/issues/463), [#362](https://github.com/ansible/ansible-creator/issues/362), [#363](https://github.com/ansible/ansible-creator/issues/363) all request a way to opt into a minimal scaffold.

## Solution

Add `--minimal` / `-m` flag to `init collection` and `init playbook`. When set, scaffold only essential structure — no example filler. Works with the existing `ansible-creator add` composable workflow (add roles, plugins, devcontainer, etc. after init).

Does **not** apply to `init execution-env` (already lean).

## Architecture

Two-level filtering, both happening in `Init._scaffold()`:

### Level 1: Common resource filtering

The `common_resources` class attribute defines shared resources included for all project types. When `--minimal`, keep only `common.gitignore` — drop devcontainer, devfile, vscode, ai, and role.

```python
# Full (default)
common_resources = ("common.devcontainer", "common.devfile", "common.gitignore", "common.vscode", "common.ai")

# Minimal
common_resources = ("common.gitignore",)
```

For collections, `common.role` is also appended in full mode but skipped in minimal.

### Level 2: Project-specific file filtering (allowlist)

After `walker.collect_paths()` returns, filter the `FileList` to keep only files whose destination path matches a known-essential allowlist. This follows the existing `filter_ee_ci_paths_for_scm()` pattern in `utils.py`.

**Collection allowlist** — paths relative to project root that pass the filter:

| Path | Reason |
|------|--------|
| `galaxy.yml` | Collection metadata (required) |
| `meta/runtime.yml` | Runtime requirements (required) |
| `changelogs/config.yaml` | Changelog config |
| `plugins/modules/__init__.py` | Module namespace init |
| `plugins/module_utils/__init__.py` | Module utils namespace init |
| `tests/.gitignore` | Test directory gitignore |
| `tests/unit/__init__.py` | Unit test namespace |
| `tests/unit/.keep` | Keep unit test dir |
| `tests/integration/__init__.py` | Integration test namespace |
| `docs/.keep` | Keep docs dir |
| `README.md` | Documentation |
| `LICENSE` | License |
| `CHANGELOG.rst` | Changelog |

Excluded: sample plugins, sample modules, action/cache/filter/inventory/lookup/plugin_utils/sub_plugins/test plugin dirs, extensions (molecule, eda), CI workflows, linting configs (pyproject.toml, .isort.cfg, .prettierignore, .pre-commit-config.yaml, tox-ansible.ini), requirements.txt, test-requirements.txt, CODE_OF_CONDUCT, CONTRIBUTING, MAINTAINERS, docs/docsite, test files (test_basic.py, test_integration.py, integration targets).

**Playbook allowlist** — paths relative to project root:

| Path | Reason |
|------|--------|
| `ansible.cfg` | Ansible config |
| `ansible-navigator.yml` | Navigator config |
| `site.yml` | Main playbook |
| `collections/requirements.yml` | Collection dependencies |
| `inventory/hosts.yml` | Inventory hosts |
| `inventory/group_vars/all.yml` | Global group vars |
| `README.md` | Documentation |

Excluded: example playbooks (linux_playbook.yml, network_playbook.yml), argspec validation plays + inventory, fake host_vars (server1-3, switch1-2), extra group_vars (db_servers, web_servers, production, test), embedded collection (collections/ansible_collections/), CI workflows.

### Filtering implementation

Add a new function `filter_minimal_paths()` in `utils.py` next to the existing `filter_ee_ci_paths_for_scm()`. It takes the `FileList`, the project type, and the init path, and returns a filtered `FileList`.

The matching logic: for each `DestinationFile`, compute the path relative to `init_path`, strip the `.j2` suffix (already done by Walker), and check if any allowlist entry matches as a suffix of the path. Directory entries (is_dir) pass if they're ancestors of any allowlisted file.

## Files to modify

| File | Change |
|------|--------|
| `src/ansible_creator/arg_parser.py` | Add `--minimal` / `-m` to `_add_args_init_common()` |
| `src/ansible_creator/config.py` | Add `minimal: bool = False` to `Config` dataclass |
| `src/ansible_creator/subcommands/init.py` | Store `self._minimal` from config; filter `common_resources` and call `filter_minimal_paths()` in `_scaffold()` |
| `src/ansible_creator/utils.py` | Add `MINIMAL_COLLECTION_INCLUDE`, `MINIMAL_PLAYBOOK_INCLUDE` constants and `filter_minimal_paths()` function |
| `tests/units/test_init.py` | Add test cases for minimal collection and playbook |

## Testing strategy

1. **Unit tests**: Create tests that init a collection and playbook with `minimal=True`, then verify:
   - All allowlisted files exist
   - No excluded files exist (spot-check sample_module, sample_filter, devcontainer, linux_playbook, fake host_vars)
   - Generated files are valid (galaxy.yml parses, README exists)
2. **Existing tests unchanged**: `minimal=False` (default) produces the same output as before — no regression
3. **Test fixtures**: Create minimal fixture directories or use dynamic assertions (preferred to avoid fixture maintenance burden)

## Edge cases

- `--minimal` with `--overwrite`: works as expected — overwrites only the minimal set
- `--minimal` with `--no-overwrite`: works as expected — checks conflicts only for minimal files
- `--minimal` has no effect on `init execution-env` (not wired up)
- Future-proofing: when new essential files are added to resources upstream, they must be added to the allowlist — this is intentional (safer to miss a new file than to include unwanted demo content)
