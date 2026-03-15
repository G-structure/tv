"""Layout and compatibility tests for the canonical `tv.*` modules."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_legacy_training_directory_is_gone():
    assert not (Path(__file__).resolve().parent.parent / "training").exists()


def test_tv_common_imports_work():
    from tv.common.config import get_repo_root

    assert (get_repo_root() / "pyproject.toml").exists()


def test_tv_training_stage_a_imports_work():
    from tv.training.stage_a_mt.build_data import _stable_hash

    assert _stable_hash("tvl") == _stable_hash("tvl")


def test_tv_training_common_shim_resolves_to_tv_common():
    from tv.training.common.config import get_repo_root as compat_get_repo_root
    from tv.common.config import get_repo_root as canonical_get_repo_root

    assert compat_get_repo_root() == canonical_get_repo_root()
