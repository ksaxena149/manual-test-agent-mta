import argparse

from mta import __version__


def main() -> None:
    parser = argparse.ArgumentParser(prog="mta", description="Manual Test Agent")
    parser.add_argument("--version", action="version", version=f"mta {__version__}")
    parser.parse_args()
