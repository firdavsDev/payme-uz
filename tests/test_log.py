from pathlib import Path

import payme
import payme.log as payme_log
from payme.log import resolve_log_file


def test_package_reexports():
    assert payme.PaymeAPIClient is not None
    assert payme.PaymeErrorCode.SUCCESS.value == 200
    assert payme.setup_logger is payme_log.setup_logger


def test_resolve_log_file_defaults_to_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PAYME_LOG_DIR", raising=False)

    path = resolve_log_file()

    assert path == (tmp_path / "logs" / "payme.log").resolve()
    assert path.parent.is_dir()
    # Must never write next to the installed package.
    assert Path(payme_log.__file__).parent not in path.parents


def test_resolve_log_file_honours_env_and_explicit_path(tmp_path, monkeypatch):
    monkeypatch.setenv("PAYME_LOG_DIR", str(tmp_path / "from-env"))
    assert resolve_log_file() == (tmp_path / "from-env" / "payme.log").resolve()

    explicit = (tmp_path / "custom" / "app.log").resolve()
    assert resolve_log_file(explicit) == explicit
    assert explicit.parent.is_dir()
