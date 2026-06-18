<div align="right">

**comMS documentation:** _Configuration_ · [Configuration reference](./config-reference.md) · [Commands](./commands.md) · [Output structure](./output-structure.md) · [README](../README.md)

</div>

# Configuration

comMS works out where to read its settings and where to write its results from a single **experiment directory**. This page explains: what an experiment context is, what makes a directory an experiment, how configuration files are layered, how the binary directory is located, and the two commands used to create or edit configurations.

For the full list of values you can set, see the [configuration reference](./config-reference.md).

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

[files]
sample_sheet = "/path/to/my_experiment/comms/sample_sheet.tsv"
config = "/path/to/my_experiment/comms/config.toml"
```

The simplest way to create an experiment directory is the [`experiment` command](#creating-an-experiment-the-experiment-command), which writes all three files.

## Configuration files
comMS reads its settings from a TOML file. Three sources can supply that file:

- **Bundled defaults.** A default `config.toml` ships inside the package and provides the baseline values. It is never edited directly.
- **Global user configuration.** A per-user file created with `comms config init`. It applies to every run unless an experiment provides its own local configuration file. Its location depends on the operating system:

    OS | Path
    -- | --
    Linux/macOS | `~/.config/comms/config.toml`
    Windows | `%APPDATA%\comms\config.toml`

- **Local configuration.** A `config.toml` inside an experiment's `comms/` folder. It applies only to that experiment. A local file is written by the [`experiment` command](#creating-an-experiment-the-experiment-command), or created with `comms config init -c <path>`.

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
The `config` command edits individual sections of a single configuration file. By default it targets the global user file. Pass `-c` / `--config` with a path to target a local file instead, or `-c global` to be explicit about the global one.

Subcommand | Purpose
---|---
`init` | Create a configuration file from the defaults (will not overwrite an existing file)
`exists` | Report whether the file exists and print its path
`list` | Print current values, highlighting any that differ from the defaults
`verify` | Check that all expected keys are present
`reset` | Overwrite the file with the defaults (prompts unless `--force`)
`set` | Change values via named flags

For example, to view the global configuration, then enable methionine oxidation and cysteine carbamidomethylation in an experiment's local file:

```bash
comms config list
comms config set -c my_experiment/comms/config.toml --ox --iodo
```

The full set of `config set` flags, the modifications they apply, and the default parameters are documented in the [configuration reference](./config-reference.md).

## Creating an experiment: the `experiment` command
The `experiment` command builds a complete experiment directory, writing the sample sheet, a local `config.toml`, and `experiment.toml` under `<dir>/comms/`. It saves manually writing the sample sheet or running `config` for each value.

```bash
comms experiment            # graphical setup
comms experiment --headless # terminal prompts only
```

The graphical setup walks through naming the experiment and choosing an output directory, defining treatment and fraction groups, importing a directory of `.RAW` / `.mzML` files, assigning each sample to its groups (replicate numbers auto-assign per treatment and fraction and can be overridden), and previewing the sheet before saving. A configuration panel mirrors `comms config set`, so the local `config.toml` it writes uses the same options.

## `config` vs `experiment`
The two commands serve different purposes:

Command | Use it to | Writes
---|---|---
`config` | Edit individual sections of an existing file, global or local | One configuration file
`experiment` | Create a new experiment from scratch | `sample_sheet.tsv`, `config.toml`, and `experiment.toml`

In short, `experiment` sets up an experiment and its local configuration, and `config` adjusts a configuration file that already exists.

---

<div align="right">

**comMS documentation:** _Configuration_ · [Configuration reference](./config-reference.md) · [Commands](./commands.md) · [Output structure](./output-structure.md) · [README](../README.md)

</div>