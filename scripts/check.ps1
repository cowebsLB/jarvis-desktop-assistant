$ErrorActionPreference = "Stop"

$python = "C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$ruff = "C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Scripts\ruff.exe"
$build = "C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Scripts\pyproject-build.exe"

& $python -m pytest
& $ruff check src tests
& $build
