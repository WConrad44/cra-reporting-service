from __future__ import annotations

from pathlib import Path
from threading import Lock

from coverage import Coverage


_APP_ROOT = Path(__file__).resolve().parent
_lock = Lock()
_coverage = Coverage(
    source=[str(_APP_ROOT)],
    omit=[str(_APP_ROOT / "routes" / "cross_team.py")],
    data_file=None,
)
_running = False


def _source_files() -> list[Path]:
    excluded = (_APP_ROOT / "routes" / "cross_team.py").resolve()
    return [
        path.resolve()
        for path in _APP_ROOT.rglob("*.py")
        if path.resolve() != excluded
    ]


def start_session_coverage() -> None:
    """Reset and begin source-line coverage for one system test session."""
    global _running

    with _lock:
        if _running:
            _coverage.stop()
        _coverage.erase()
        _coverage.start()
        _running = True


def code_coverage_measure() -> dict[str, int | str]:
    """Return line coverage without counting the /test/report request itself."""
    global _running

    with _lock:
        if _running:
            _coverage.stop()
            _running = False

        data = _coverage.get_data()
        measured_lines = {
            Path(filename).resolve(): set(data.lines(filename) or [])
            for filename in data.measured_files()
        }

        covered = 0
        total = 0
        for path in _source_files():
            try:
                _, statements, _, _, _ = _coverage.analysis2(str(path))
            except Exception:
                continue
            statement_lines = set(statements)
            total += len(statement_lines)
            covered += len(statement_lines & measured_lines.get(path, set()))

        # Later project requests in the same prepared session may increase coverage.
        _coverage.start()
        _running = True

        return {
            "covered": covered,
            "total": total,
            "basis": (
                "Source-line coverage for the Team 21 app package, excluding the "
                "course /test setup/report implementation so reading coverage does not "
                "change the measurement."
            ),
        }
