# Runs the load test in steps against the scratch database (#224).
# From the repository root, after scratch_db.py create and setup_users.py:
#   powershell -File scripts\load_test\run_steps.ps1 -UsersFile <users.json> -OutDir <dir>
# Starts runserver on 127.0.0.1:8001 with DB_NAME=nurtura_loadtest, DEBUG off
# and the model warmed up, then for each step runs Locust headless for
# -Seconds while sampling the server's memory and CPU, and stops the server.
param(
    [Parameter(Mandatory)] [string]$UsersFile,
    [Parameter(Mandatory)] [string]$OutDir,
    [int[]]$Steps = @(10, 25, 50, 100),
    [int]$Seconds = 120,
    [int]$SpawnRate = 5
)

$ErrorActionPreference = "Stop"
$py = (Resolve-Path "backend\venv\Scripts\python.exe").Path
$lt = (Resolve-Path "scripts\load_test\.venv\Scripts\python.exe").Path
New-Item -ItemType Directory -Force $OutDir | Out-Null

$env:DB_NAME = "nurtura_loadtest"
$env:DEBUG = "False"
$env:SECRET_KEY = "loadtest-only-" + [guid]::NewGuid().ToString("N")
$env:ALLOWED_HOSTS = "127.0.0.1,localhost"
$env:NURTURA_MODEL_WARMUP = "1"
$env:EMAIL_HOST = ""
$env:LOADTEST_USERS = (Resolve-Path $UsersFile).Path

$server = Start-Process -FilePath $py -ArgumentList "manage.py", "runserver", "127.0.0.1:8001", "--noreload" `
    -WorkingDirectory "backend" -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput "$OutDir\server_out.txt" -RedirectStandardError "$OutDir\server_err.txt"
try {
    $started = Get-Date
    while ($true) {
        try {
            Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8001/api/privacy-notice/" -TimeoutSec 5 | Out-Null
            break
        } catch {
            if (((Get-Date) - $started).TotalSeconds -gt 180) { throw "server didn't start" }
            Start-Sleep -Seconds 2
        }
    }
    "server ready after {0:N0} s" -f ((Get-Date) - $started).TotalSeconds | Tee-Object "$OutDir\startup.txt"

    foreach ($n in $Steps) {
        $mem = Start-Process -FilePath $lt -ArgumentList "scripts\load_test\peak_memory.py", $server.Id, ($Seconds + 5), "$OutDir\memory_$n.json" `
            -PassThru -WindowStyle Hidden
        # Locust logs to stderr, so run it as its own process rather than
        # letting PowerShell treat the log as an error.
        Start-Process -FilePath $lt -Wait -WindowStyle Hidden `
            -ArgumentList "-m", "locust", "-f", "scripts\load_test\locustfile.py", "--headless", `
                "-u", $n, "-r", $SpawnRate, "-t", "${Seconds}s", "--host", "http://127.0.0.1:8001", `
                "--csv", "$OutDir\step_$n", "--only-summary" `
            -RedirectStandardOutput "$OutDir\locust_${n}_out.txt" -RedirectStandardError "$OutDir\locust_$n.txt"
        $mem.WaitForExit()
        "step $n done"
    }
} finally {
    Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
}
