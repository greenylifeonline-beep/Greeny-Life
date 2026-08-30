import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".ai-os" / "control"))

import pytest

from c2_obs import join  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def c2_obs_join():
    rec = join()
    assert rec["lease_ok"] is True
    assert rec["channel_isolated_ok"] is True
    return rec
