# Design: `--minimal` flag for `init collection` and `init playbook`

## Problem

`ansible-creator init collection` scaffolds 60+ files including sample plugins, stub roles, EDA rulebooks, molecule tests, devcontainer configs, and CI workflows. Experienced users must immediately clean up the noise. Upstream issues [#463](https://github.com/ansible/ansible-creator/issues/463), [#362](https://github.com/ansible/ansible-creator/issues/362), [#363](https://github.com/ansible/ansible-creator/issues/363) all request a way to opt into a minimal scaffold.

## Solution

Add `--minimal` / `-m` flag to `init collection` and `init playbook`. When set, scaffold only the essential project structure plus `.gitignore`.

`--minimal` is a subset of the resource selection. The project resource directories (`collection_project/`, `playbook_project/`) get restructured to contain **only essential files**. All non-essential content moves into scoped resource directories — the same mechanism that already handles `common.devcontainer`, `common.role`, etc.

```python
# --minimal
resources = ("collection_project", "common.gitignore")

# full (default, same behavior as today)
resources = ("collection_project", *common_resources,
             "collection.samples", "collection.ci", "collection.eda",
             "collection.molecule", "collection.tooling", "collection.community")
```

No filtering layer, no allowlist — just resource selection.

Does **not** apply to `init execution-env` (already lean).

### How this addresses upstream concerns

- **Implements the category-based approach** ([#463](https://github.com/ansible/ansible-creator/issues/463)) — the Community Engineering team proposed starting minimal and adding categories selectively (modules, roles, EDA, tests, CI, galaxy publishing). The scoped resource directories (`collection.samples`, `collection.eda`, `collection.ci`, etc.) directly implement these categories as modular, composable resources.
- **Avoids CLI flag explosion** ([#362](https://github.com/ansible/ansible-creator/issues/362#issuecomment-2718004381)) — a single `--minimal` flag instead of per-resource `--no-role`, `--no-eda`, `--no-devcontainer`, etc. Users compose what they need post-init via `ansible-creator add resource`.
- **Preserves all user personas** ([#363](https://github.com/ansible/ansible-creator/issues/363#issuecomment-2718023364)) — the default (full) behavior is unchanged. Devcontainer, devfile, and devspaces users get everything they expect. Minimal is opt-in.
- **Complements the planned overlay approach** ([#374](https://github.com/ansible/ansible-creator/issues/374#issuecomment-3127244836)) — modularizing resources into scoped directories is groundwork that makes overlays, custom templates, and future `add resource` extensions all possible. The overlay adds files on top; `--minimal` controls which built-in resources to start with. They work together.
- **Enables template customization** ([#70](https://github.com/ansible/ansible-creator/issues/70#issuecomment-1905999556)) — the modular resource structure makes it easier to override or replace individual categories in the future, moving toward the per-category template sources requested here.
- **Aligns with `ansible-galaxy collection init`** — which already defaults to a minimal scaffold. This closes the UX gap between the two tools.
- **Consistent with `collection_template`** ([ansible-collections/collection_template](https://github.com/ansible-collections/collection_template)) — the community's reference template for new collections contains no sample code, no devcontainer, no devfile, no EDA, no molecule, and no linting tooling configs. Our minimal scaffold follows the same principle: essential structure only, no filler. To replicate the `collection_template` structure using this composable workflow, a user would run `init collection --minimal` and then add the resources that already exist today: `add resource devcontainer`, `add resource role`, etc. The CI and community files that `collection_template` includes would become available once the follow-up `add resource` types are implemented.

## Resource namespacing

Resources are namespaced by scope to keep the hierarchy meaningful:

| Scope | Pattern | Meaning |
|-------|---------|---------|
| `common.*` | Shared across project types | `common.gitignore`, `common.devcontainer`, `common.devfile`, `common.vscode`, `common.ai`, `common.role` |
| `collection.*` | Collection-specific optional | `collection.samples`, `collection.ci`, `collection.eda`, `collection.molecule`, `collection.tooling`, `collection.community` |
| `playbook.*` | Playbook-specific optional | `playbook.examples`, `playbook.inventory-examples`, `playbook.ci`, `playbook.collection` |

Directory structure on disk:

```
resources/
├── collection_project/       # essential collection files
├── collection/               # collection-specific optional resources
│   ├── samples/
│   ├── ci/
│   ├── eda/
│   ├── molecule/
│   ├── tooling/
│   └── community/
├── playbook_project/         # essential playbook files
├── playbook/                 # playbook-specific optional resources
│   ├── examples/
│   ├── inventory-examples/
│   ├── ci/
│   └── collection/
├── common/                   # shared across project types (unchanged)
│   ├── devcontainer/
│   ├── devfile/
│   ├── gitignore/
│   ├── vscode/
│   ├── ai/
│   ├── role/
│   ├── ee-ci/
│   ├── execution-environment/
│   └── play-argspec/
└── execution_env_project/
```

The Walker already supports this — `collection.samples` resolves to `ansible_creator.resources.collection.samples` via `importlib.resources`.

## Composable workflow

`--minimal` works with `ansible-creator add`:

1. `ansible-creator init collection ns.name path --minimal` — bare essential structure
2. `ansible-creator add resource role myrole path` — add roles as needed
3. `ansible-creator add plugin module mymod path` — add plugins as needed
4. `ansible-creator add resource devcontainer path` — add devcontainer when needed

Not all new resource categories have `add resource` equivalents yet. New `add resource` types are follow-up work — this PR makes them possible by modularizing the resources.

## What stays in `collection_project/`

Only files required for a valid, buildable collection:

```
collection_project/
├── galaxy.yml.j2
├── meta/runtime.yml
├── changelogs/config.yaml.j2
├── plugins/
│   ├── modules/__init__.py.j2
│   └── module_utils/__init__.py.j2
├── tests/
│   ├── .gitignore
│   ├── unit/__init__.py
│   ├── unit/.keep
│   └── integration/__init__.py.j2
├── docs/.keep
├── README.md.j2
├── LICENSE.j2
└── CHANGELOG.rst
```

## What moves from `collection_project/` into `collection.*`

| New resource | Files | Notes |
|---|---|---|
| `collection.samples` | `plugins/{action,cache,filter,inventory,lookup,plugin_utils,sub_plugins,test}/` (all `__init__.py` + `sample_*.py`), `plugins/modules/sample_*.py`, `tests/unit/test_basic.py`, `tests/integration/test_integration.py`, `tests/integration/targets/` | All demo/example content |
| `collection.ci` | `.github/workflows/release.yml`, `.github/workflows/tests.yml` | CI workflows |
| `collection.eda` | `extensions/eda/rulebooks/rulebook.yml` | Event-Driven Ansible |
| `collection.molecule` | `extensions/molecule/` (all files) | Molecule testing |
| `collection.tooling` | `pyproject.toml`, `.isort.cfg`, `.prettierignore`, `.pre-commit-config.yaml`, `tox-ansible.ini`, `requirements.txt`, `test-requirements.txt` | Linting and dev tool configs |
| `collection.community` | `CODE_OF_CONDUCT.md`, `CONTRIBUTING`, `MAINTAINERS`, `docs/docsite/links.yml` | Galaxy/community files |

## What stays in `playbook_project/`

Only files required for a working playbook project:

```
playbook_project/
├── ansible.cfg.j2
├── ansible-navigator.yml.j2
├── site.yml.j2
├── collections/requirements.yml.j2
├── inventory/
│   ├── hosts.yml.j2
│   └── group_vars/all.yml.j2
└── README.md.j2
```

## What moves from `playbook_project/` into `playbook.*`

| New resource | Files | Notes |
|---|---|---|
| `playbook.examples` | `linux_playbook.yml`, `network_playbook.yml` | Example playbooks |
| `playbook.inventory-examples` | `inventory/group_vars/{db_servers,production,test,web_servers}.yml`, `inventory/host_vars/{server1,server2,server3,switch1,switch2}.yml` | Fake hosts/groups |
| `playbook.ci` | `.github/ansible-code-bot.yml`, `.github/workflows/tests.yml` | Playbook CI |
| `playbook.collection` | `collections/ansible_collections/` (embedded collection + role) | Adjacent collection |

Note: `argspec_validation_plays.*` and `inventory/argspec_validation_inventory.yml` are duplicated between `playbook_project/` and `common.play-argspec`. Remove the duplicates from `playbook_project/` — use `common.play-argspec` resource instead.

## `_scaffold()` changes

```python
common_resources: tuple[str, ...] = (
    "common.devcontainer",
    "common.devfile",
    "common.gitignore",
    "common.vscode",
    "common.ai",
)

collection_resources: tuple[str, ...] = (
    "common.role",
    "collection.samples",
    "collection.ci",
    "collection.eda",
    "collection.molecule",
    "collection.tooling",
    "collection.community",
)

playbook_resources: tuple[str, ...] = (
    "common.play-argspec",
    "playbook.examples",
    "playbook.inventory-examples",
    "playbook.ci",
    "playbook.collection",
)

def _scaffold(self) -> None:
    # ...
    if self._project == "execution_env":
        resources = (f"{self._project}_project", "common.ee-ci")
    elif self._minimal:
        resources = (f"{self._project}_project", "common.gitignore")
    elif self._project == "collection":
        resources = (
            f"{self._project}_project",
            *self.common_resources,
            *self.collection_resources,
        )
    else:  # playbook
        resources = (
            f"{self._project}_project",
            *self.common_resources,
            *self.playbook_resources,
        )
```

## Files to modify

| File | Change |
|------|--------|
| `src/ansible_creator/arg_parser.py` | Add `--minimal` / `-m` to `_add_args_init_common()` |
| `src/ansible_creator/config.py` | Add `minimal: bool = False` to `Config` dataclass |
| `src/ansible_creator/subcommands/init.py` | Store `self._minimal`; add `collection_resources` and `playbook_resources` tuples; branch resource selection in `_scaffold()` |
| `src/ansible_creator/resources/collection_project/` | Remove non-essential files |
| `src/ansible_creator/resources/collection/` | New package: `samples/`, `ci/`, `eda/`, `molecule/`, `tooling/`, `community/` with moved files |
| `src/ansible_creator/resources/playbook_project/` | Remove non-essential files, remove argspec duplicates |
| `src/ansible_creator/resources/playbook/` | New package: `examples/`, `inventory-examples/`, `ci/`, `collection/` with moved files |
| `tests/units/test_init.py` | Update for restructured resources; add minimal mode tests |

## Testing strategy

1. **Full mode must produce identical output** — restructuring resources must not change what `init collection` and `init playbook` produce by default. Compare against existing test fixtures.
2. **Minimal mode tests** — verify only essential files are scaffolded, no extras.
3. **`add resource` still works** — existing add commands unaffected.

## Edge cases

- `--minimal` with `--overwrite` / `--no-overwrite`: works as expected
- `--minimal` has no effect on `init execution-env` (not wired up)
- Default behavior (no `--minimal` flag) produces exactly the same output as before — no regression
- `add plugin action myaction` after minimal init works — `add.py` creates `plugins/{type}/` directory with `mkdir(parents=True)`

## Future work (not this PR)

- New `add resource` subcommands for: `collection.samples`, `collection.ci`, `collection.eda`, `collection.molecule`, `collection.tooling`, `collection.community`, `playbook.examples`, `playbook.inventory-examples`, `playbook.ci`, `playbook.collection`
- Combined init syntax: `init collection ns.name --add role,devcontainer,ci`
- Consider making minimal the default and adding `--full` flag (per upstream #463 direction)
