"""Byte-level guards for source files synchronized from production.

These hashes are the SHA-256 values of the files on the production server at
the time of the 2026-10-23 synchronization.  The files are intentionally kept
verbatim, including their original formatting and line endings.  A failure
here means the published GitHub source no longer matches the recorded
production baseline; update this test only after a deliberate production
change and a documented re-synchronization.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

PRODUCTION_HASHES = {
    "realtime_capitulation_monitor_fixed.py": "f661e3796f9285dc3fc592714bc980d7734ec8dae61b6dcbd2863083d3de8204",
    "config/__init__.py": "35e3ae3fd2851525ecf6741ab834a63fcc6b722ca40b95f62ffd955035561b23",
    "config/capitulation_thresholds.py": "bc51b6972d243bb18eee1165579b18899597cd9b67d423dae0017bb0e62a0b5e",
    "src/config/capitulation_thresholds.py": "bc51b6972d243bb18eee1165579b18899597cd9b67d423dae0017bb0e62a0b5e",
    "src/strategy/__init__.py": "db6101ff709de19a0d3d2ccb3e671c926259eacb5f607004bf885ff7cb6e9d8d",
    "src/strategy/capitulation_detector.py": "3b239a003ee20873178ae2e0aad15784556658fb5b343bc98e4d1e843ace0539",
    "src/exchange/__init__.py": "eb8ea474128749befcd3d052499ae3b1504c226edf7c746217dd4b2931acffd5",
    "src/exchange/bingx_fetcher.py": "89369399e2521a8fa0e9b3aaf6faba05221e7d1090660bccc13e122050c6a14d",
    "src/exchange/bingx_rate_limiter.py": "bd77f0516baf1bb4f058f5b88f857d5b015cf8fc32334d9ec30cf20cdfd5c3a6",
    "src/exchange/bingx_endpoints.py": "cdc63bc050cf58f23aeb692b8f1dc18962ded5f58e3cfdc622c534eeafc7405a",
    "src/data_provider/__init__.py": "2039e99ffed561d8414b6eb16df914d7115c8de7a050b9b939fdc0c06949ba56",
    "src/data_provider/universe_provider.py": "9ca77e0b80b4f8859b57163324c8cf0ce7a831ed1e0112cf49c4d06ed2f0c0aa",
    "src/data_provider/cmc_universe_cache.py": "da46289b9eb1880091e56fa1d88f43ebb56234c2fe02d6dac1067de34fad58d3",
    "evreconse.service": "adc9201cca8a299c3da4aa7b70ddbf1efe5eb70f62eb5969844e23ed8c14e51c",
    "requirements-production-freeze.txt": "6e638060c003708658e1e10ca9ed020df24ca9324277dc6e18412aa2a04ad41e",
}


@pytest.mark.parametrize(("relative_path", "expected"), PRODUCTION_HASHES.items())
def test_production_file_hash(relative_path: str, expected: str) -> None:
    data = (ROOT / relative_path).read_bytes()
    assert hashlib.sha256(data).hexdigest() == expected


def test_active_detector_resolves_the_production_config_package() -> None:
    """The monitor inserts the repo root before ``src`` via the detector.

    Production has a top-level ``config`` package with only the Capitulation
    thresholds.  The active detector must resolve that package, not the larger
    ``src/config`` application package.  Run in a fresh interpreter because
    pytest may already have imported ``src/config`` through conftest.
    """
    code = """
import sys
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "src")
from src.strategy.capitulation_detector import check_capitulation_signal
import config
print(Path(config.__file__).resolve())
"""
    result = subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert Path(result.stdout.strip()) == (ROOT / "config" / "__init__.py").resolve()
