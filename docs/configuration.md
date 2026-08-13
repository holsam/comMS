<div align="right">

**comMS documentation:** [Commands][docs-commands] · _Configuration_ · [Configuration reference][docs-config-ref] · [Output structure][docs-output] · [README][docs-readme]

</div>

# Configuration

comMS works out where to read its settings and where to write its results from a single **experiment directory**. This page explains: what an experiment context is, what makes a directory an experiment, how configuration files are layered, how the binary directory is located, and the two commands used to create or edit configurations.

For the full list of values you can set, see the [configuration reference][docs-config-ref].

## Contents
- [Experiment context](#experiment-context)
- [Experiment directories](#experiment-directories)
- [Configuration files](#configuration-files)
- [Bin directory resolution](#bin-directory-resolution)
- [Editing configuration: the `config` command](#editing-configuration-the-config-command)
- [Creating an experiment: the `experiment` command](#creating-an-experiment-the-experiment-command)
- [`config` vs `experiment`](#config-vs-experiment)

## Experiment context
An **experiment context** is a resolved view of one experiment directory. It carries that experiment's configuration, its binary directory, and its output root, along with any metadata read from `experiment.toml`.

Every command resolves this context once when it starts, and then threads it through the work it does. The resolved directory is provided via the `-e` / `--experiment-dir` option, which defaults to the current working directory. A resolved context holds:

Field | Meaning
---|---
`root` | The output root. Results are written under `<root>/comms/results/<command>/`
`comms_dir` | The `comms/` folder holding `experiment.toml`, `config.toml`, and the sample sheet
`config` | The active configuration, already resolved (see [Configuration files](#configuration-files))
`bin_dir` | The binary directory, if one is set in `experiment.toml`
`metadata` | The parsed contents of `experiment.toml`, where present

Because the context is resolved once and reused, every stage of a run reads the same configuration and writes to the same place.

## Experiment directories
A directory becomes an experiment when its `comms/` subfolder contains an `experiment.toml` file. That subfolder is where comMS keeps everything specific to the experiment:

```
my_experiment/
   └─ comms/
      ├─ experiment.toml      # experiment metadata
      ├─ config.toml          # local configuration (optional)
      ├─ sample_sheet.tsv     # sample sheet
      └─ results/             # all command outputs
```

The experiment root (`my_experiment/`) or the `comms/` folder itself can be passed to `--experiment-dir`, with both resolving to the same context. This avoids results being nested as `comms/comms/`. If no `--experiment-dir` is provided, the current directory becomes the root and outputs go to `./comms/results/`.

`experiment.toml` records the experiment name, the time it was last updated, an optional binary directory, and the paths to its sample sheet and configuration:

```toml
[experiment]
name = "Example comMS experiment"
updated = "2025-10-01T12:00:00+00:00"
bin_dir = "/absolute/path/to/comMS/bin"   # optional
analysis = "multi"

[files]
sample_sheet = "/path/to/my_experiment/comms/sample_sheet.tsv"
config = "/path/to/my_experiment/comms/config.toml"
database = "/path/to/protein/database.fasta"
data = ["/path/to/data/sample1.RAW", "/path/to/data/sample2.RAW"]

[report]
enabled = True
ref_info = "/path/to/reference/protein/annotations.tsv"
cont_csv = "/path/to/contaminants/info.csv"
organism_prefix = "ID_PREFIX"
```

The simplest way to create an experiment directory is the [`experiment` command](#creating-an-experiment-the-experiment-command), which writes all three files.

## Configuration files
comMS reads its settings from a TOML file. Three sources can supply that file:

- **Bundled defaults.** A default `config.toml` ships inside the package and provides the baseline values. It is never edited directly.
- **Global user configuration.** A per-user file created with `comms config --global`. It applies to every run unless an experiment provides its own local configuration file. Its location depends on the operating system:

    OS | Path
    -- | --
    Linux/macOS | `~/.config/comms/config.toml`
    Windows | `%APPDATA%\comms\config.toml`

- **Local configuration.** A `config.toml` inside an experiment's `comms/` folder. It applies only to that experiment. A local file is written by the [`experiment` command](#creating-an-experiment-the-experiment-command), or created by pointing `comms config` at the experiment directory (e.g. `comms config <path>`), which creates the file from defaults if it doesn't already exist.

### Resolution order
For any given run, comMS uses the first configuration it finds, in this order:

Priority | Source | Location
-- | -- | --
1 | Local | `<experiment>/comms/config.toml`
2 | Global | OS user config path (see above)
3 | Bundled default | Shipped with the package

An experiment's own `config.toml` takes precedence over a global file, which in turn takes precedence over the built-in defaults. Run with `-vv` to see which source was chosen, reported in the debug log.

## Bin directory resolution
The external binaries (Crux and ThermoRawFileParser) are found from a `bin/` directory, resolved in this order:

Priority | Source
---|---
1 | `bin_dir` set under `[experiment]` in `experiment.toml`
2 | The `COMMS_BIN_DIR` environment variable
3 | The repository's own `bin/` directory

The third option only works when comMS is run from a development checkout. Because `uv tool install` installs comMS outside the cloned repository, an installed copy cannot see the repository's `bin/`, so set `bin_dir` in `experiment.toml` or export `COMMS_BIN_DIR`:

```bash
export COMMS_BIN_DIR=/absolute/path/to/comMS/bin
```

## Editing configuration: the `config` command
`config` is a single command, not a set of subcommands: it edits or inspects one configuration file, and which behaviour you get depends on which flags you pass.

```bash
comms config [PATH] [--global] [--verify | --reset [--force]] [protocol/value flags...]
```

Argument/flag | Purpose
---|---
`PATH` (positional, optional) | Experiment directory whose local `config.toml` should be targeted. Defaults to the current directory.
`--global` | Target the global user config instead of a local one.
`--verify` | Check that all expected keys are present in the target file (and no unexpected ones), then exit.
`--reset` | Overwrite the target file with comMS defaults (prompts for confirmation unless `--force` is also given), then exit.
`--force` | Skip the confirmation prompt when used with `--reset`.
*(any protocol/value flag, e.g. `--ox`, `--iodo`, `--organism`)* | Apply that value to the target file.

If none of `--verify`, `--reset`, or a value-setting flag is given (or a value-setting flag is given but resolves to no change), `config` falls back to listing the current values against the defaults — this is also what running `comms config` on its own does.

**Resolving which file to edit.** Without `PATH` or `--global`, `config` looks in the current directory for a bare `config.toml` or a `config.toml` nested under `comms/`. If neither exists, it offers to create one at `<cwd>/comms/config.toml`. If a path or `--global` is given and the target file doesn't exist yet, it is created from the bundled defaults first.

For example, to view the global configuration, then enable methionine oxidation and cysteine carbamidomethylation in an experiment's local file:

```bash
comms config --global
comms config my_experiment --ox --iodo
```

To check a config file is complete, or reset it to defaults:

```bash
comms config my_experiment --verify
comms config my_experiment --reset --force
```

The full set of value-setting flags, the modifications they apply, and the default parameters are documented in the [configuration reference][docs-config-ref].

## Creating an experiment: the `experiment` command
The `experiment` command builds a complete experiment directory, writing the sample sheet, a local `config.toml`, and `experiment.toml` under `<dir>/comms/`. It saves manually writing the sample sheet or running `config` for each value.

```bash
comms experiment            # graphical setup
comms experiment --headless # terminal prompts only
```

Both the GUI and command-line setups walk through naming the experiment and choosing an output directory, defining treatment and fraction groups, importing a directory of `.RAW` / `.mzML` files, assigning each sample to its groups (replicate numbers auto-assign per treatment and fraction and can be overridden), and previewing the sheet before saving. A configuration panel mirrors the `comms config` value-setting flags, so the local `config.toml` it writes uses the same options. The configuration panel also includes a report settings section, where a reference annotation file (TSV/CSV), a contaminant list (CSV), and a primary organism ID prefix can be set. These are written to experiment.toml under [report] and used automatically when comms report is run against the experiment directory.

## `config` vs `experiment`
The two commands serve different purposes:

Command | Use it to | Writes
---|---|---
`config` | Edit individual sections of an existing file, global or local | One configuration file
`experiment` | Create a new experiment from scratch | `sample_sheet.tsv`, `config.toml`, and `experiment.toml`

In short, `experiment` sets up an experiment and its local configuration, and `config` adjusts a configuration file that already exists.

---

<div align="right">

**comMS documentation:** [Commands][docs-commands] · _Configuration_ · [Configuration reference][docs-config-ref] · [Output structure][docs-output] · [README][docs-readme]

</div>

<!-- MARKDOWN LINKS & IMAGES -->
[docs-commands]: ./commands.md#commands
[docs-config-ref]: ./config-reference.md#configuration-reference
[docs-config]: ./configuration.md#configuration
[docs-output]: ./output-structure.md#output-structure
[docs-readme]: ../README.md#comms