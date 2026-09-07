"""Compile app/static/css/custom.scss -> app/static/css/bulma-hunter.css.
Needs Dart Sass (`brew install dart-sass`), not LibSass.
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "app" / "static" / "css" / "custom.scss"
DEST = ROOT / "app" / "static" / "css" / "bulma-hunter.css"
LOAD_PATH = ROOT / "app" / "scss_src"  # contains bulma/, so `@use "bulma/sass"` resolves

if __name__ == "__main__":
    if shutil.which("sass") is None:
        sys.exit(
            "error: Dart Sass ('sass' CLI) not found on PATH.\n"
            "Install it with: brew install dart-sass\n"
            "(LibSass / node-sass will NOT work - Bulma 1.x requires Dart Sass's @use/@forward support.)"
        )

    result = subprocess.run(
        [
            "sass",
            f"--load-path={LOAD_PATH}",
            "--style=compressed",
            "--no-source-map",
            "--quiet-deps",  # quiets deprecation warnings from vendored Bulma, not our own scss
            str(SRC),
            str(DEST),
        ]
    )
    if result.returncode != 0:
        sys.exit(result.returncode)

    print(f"Compiled {SRC.relative_to(ROOT)} -> {DEST.relative_to(ROOT)} ({DEST.stat().st_size:,} bytes)")
