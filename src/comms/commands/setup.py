'''
comMS setup functions
'''

# -- Import external dependencies
from pathlib import Path
from rich import print
from typing import Optional
from urllib.error import URLError

# -- Import internal dependencies
from comms.utils.download import (
    CRUX_DEFAULT_VERSION,
    TRFP_DEFAULT_VERSION,
    download_crux,
    download_thermorawfileparser,
)
from comms.utils.settings import lg


# -- setup_tools: download ThermoRawFileParser and/or the Crux toolkit
def setup_tools(
    tool: str,
    trfp_version: str = TRFP_DEFAULT_VERSION,
    crux_version: str = CRUX_DEFAULT_VERSION,
    bin_dir: Optional[Path] = None,
    force: bool = False,
) -> None:
    lg.warning(f'setup | comms setup functionality is not yet supported.')
    raise NotImplementedError()
#     valid = {'all', 'crux', 'trfp'}
#     if tool not in valid:
#         raise ValueError(
#             f'{tool} is not a valid tool argument. Choose from: {", ".join(sorted(valid))}.'
#         )
#     print()
#     if tool in ('trfp', 'all'):
#         _run_trfp_download(trfp_version, bin_dir, force)
#     if tool in ("crux", 'all'):
#         _run_crux_download(crux_version, bin_dir, force)
#     print()


# # -- _run_trfp_download: download ThermoRawFileParser and report outcome to terminal
# def _run_trfp_download(
#     version: str,
#     bin_dir: Optional[Path],
#     force: bool,
# ) -> None:
#     print(f'[bold blue]Setting up ThermoRawFileParser v{version}...[/bold blue]')
#     try:
#         exe = download_thermorawfileparser(
#             version=version,
#             bin_dir=bin_dir,
#             force=force,
#         )
#         print(
#             f'[bold green]SUCCESS:[/bold green] ThermoRawFileParser ready at [cyan]{exe}[/cyan]'
#         )
#     except URLError as exc:
#         print(
#             f'[bold red]ERROR:[/bold red] Network error downloading ThermoRawFileParser: {exc}'
#         )
#         raise
#     except (RuntimeError, KeyError, FileNotFoundError) as exc:
#         print(f'[bold red]ERROR:[/bold red] {exc}')
#         raise

# # -- _run_crux_download: download Crux and report outcome to terminal
# def _run_crux_download(
#     version: str,
#     bin_dir: Optional[Path],
#     force: bool,
# ) -> None:
#     print(f'[bold blue]Setting up Crux v{version}...[/bold blue]')
#     try:
#         crux_bin = download_crux(
#             version=version,
#             bin_dir=bin_dir,
#             force=force,
#         )
#         print(
#             f'[bold green]SUCCESS:[/bold green] Crux ready at [cyan]{crux_bin}[/cyan]'
#         )
#     except NotImplementedError as exc:
#         # Windows message
#         print(f'[bold yellow]WARNING:[/bold yellow] {exc}')
#         # Re-raise so the caller knows something was skipped.
#         raise
#     except URLError as exc:
#         print(
#             f'[bold red]ERROR:[/bold red] Network error downloading Crux: {exc}'
#         )
#         raise
#     except (RuntimeError, KeyError, FileNotFoundError) as exc:
#         print(f'[bold red]ERROR:[/bold red] {exc}')
#         raise