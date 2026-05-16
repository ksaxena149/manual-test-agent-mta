import subprocess
import sys


def test_version_flag_exits_zero_and_prints_version():
    result = subprocess.run(
        [sys.executable, "-m", "mta", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert result.stdout.strip() != ""


def test_version_string_matches_package():
    import mta

    result = subprocess.run(
        [sys.executable, "-m", "mta", "--version"],
        capture_output=True,
        text=True,
    )
    assert mta.__version__ in result.stdout or mta.__version__ in result.stderr
