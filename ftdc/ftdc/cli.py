"""Command-line interface for FTDC tool."""

import sys
from pathlib import Path

import click

from .errors import FTDCError
from .service import FTDCService


@click.group()
@click.version_option(version="0.1.0")
def main():
    """FTDC tool for MongoDB Atlas - Download and convert FTDC diagnostic data."""
    pass


@main.command()
@click.option(
    "--group-key",
    "-g",
    required=True,
    help="MongoDB Atlas project/group ID (found in Atlas UI URL)",
)
@click.option(
    "--replica-set-name",
    "-r",
    required=True,
    help="Replica set or shard name (e.g., 'atlas-cluster-shard-0' or 'shard-00')",
)
@click.option(
    "--public",
    "-p",
    required=True,
    envvar="ATLAS_PUBLIC_KEY",
    help="Atlas API public key (or set ATLAS_PUBLIC_KEY env var)",
)
@click.option(
    "--private",
    "-P",
    required=True,
    envvar="ATLAS_PRIVATE_KEY",
    help="Atlas API private key (or set ATLAS_PRIVATE_KEY env var)",
)
@click.option(
    "--size",
    "-s",
    default=10_000_000,
    type=int,
    help="Byte size of data to download (default: 10,000,000)",
)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Output directory for downloaded file (default: current directory)",
)
def download(
    group_key: str,
    replica_set_name: str,
    public: str,
    private: str,
    size: int,
    output_dir: Path | None,
):
    """Download FTDC data from a MongoDB Atlas cluster.

    This command creates a log collection job on Atlas, polls for completion,
    and downloads the FTDC diagnostic data as a tar.gz file.

    Examples:

        \b
        # Download with command-line credentials
        ftdc download -g PROJECT_ID -r shard-00 -p PUBLIC_KEY -P PRIVATE_KEY

        \b
        # Download using environment variables
        export ATLAS_PUBLIC_KEY="your-public-key"
        export ATLAS_PRIVATE_KEY="your-private-key"
        ftdc download -g PROJECT_ID -r shard-00

        \b
        # Download with custom size to output directory
        ftdc download -g PROJECT_ID -r shard-00 -p KEY -P SECRET -s 50000000 -o ./data
    """
    try:
        service = FTDCService(public, private)

        file_path = service.get_ftdc_data(
            group_key=group_key,
            replica_set_name=replica_set_name,
            byte_size=size,
            output_dir=output_dir,
        )

        click.echo(f"\n Downloaded to: {file_path}")

    except FTDCError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


@main.command()
def convert():
    """Convert FTDC data to human-readable format.

    (To be implemented)
    """
    click.echo("FTDC convert command - coming soon!")
    click.echo("This will convert FTDC tar.gz files to JSON or other formats.")


if __name__ == "__main__":
    main()
