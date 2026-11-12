# Regenerates the report evidence pack (docs/report_evidence/).
# From the repository root:  powershell -File scripts\report_evidence\run_all.ps1
# Add -Reuse to rebuild the tests page from the saved test logs instead of
# running both suites again (about 10 minutes).
param([switch]$Reuse)

$ErrorActionPreference = "Stop"
$py = "backend\venv\Scripts\python.exe"
$fig = "scripts\report_evidence\.venv\Scripts\python.exe"
$env:PYTHONIOENCODING = "utf-8"

if (-not (Test-Path $fig)) {
    python -m venv scripts\report_evidence\.venv
    & $fig -m pip install -r scripts\report_evidence\requirements-figures.txt
}

$testsArgs = @()
if ($Reuse) { $testsArgs = @("--reuse") }
& $py scripts\report_evidence\tests_and_ci.py @testsArgs
foreach ($s in "environment", "catalogue_and_config", "evaluation", "latency", "explanation_examples", "workflow_transcript", "mobile_and_repo") {
    & $py "scripts\report_evidence\$s.py"
    if ($LASTEXITCODE) { throw "$s.py failed" }
}
& $fig scripts\report_evidence\make_figures.py
& $py scripts\report_evidence\build_index.py
