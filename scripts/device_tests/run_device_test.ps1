# Runs the end-to-end test on one emulated device (#230).
# From the repository root, with the backend already running on
# 127.0.0.1:8000 (EMAIL_HOST empty, console output redirected to -ServerLog):
#   powershell -File scripts\device_tests\run_device_test.ps1 -Avd nurtura_tablet `
#       -Label tablet -Port 5562 -ServerLog <log> -OutDir docs\device_tests\tablet [-FontScale 1.3]
# Boots the emulator (no window), records the device's properties, runs
# integration_test/app_flow_test.dart with flutter drive while
# type_code.py types the emailed code, saves the screenshots, the log and
# result.json to -OutDir, and shuts the emulator down.
param(
    [Parameter(Mandatory)] [string]$Avd,
    [Parameter(Mandatory)] [string]$Label,
    [Parameter(Mandatory)] [int]$Port,
    [Parameter(Mandatory)] [string]$ServerLog,
    # runserver's request log (its stderr), used to confirm the code worked.
    [Parameter(Mandatory)] [string]$RequestLog,
    [Parameter(Mandatory)] [string]$OutDir,
    [double]$FontScale = 0,
    # The prebuilt test app (see docs/device_tests.md) and the email built
    # into it. Building during a run, beside the emulator and the backend,
    # ran the laptop out of memory and killed Gradle.
    [Parameter(Mandatory)] [string]$Apk,
    [string]$Email = "device-e2e@nurtura.invalid"
)

# Continue, not Stop: in Windows PowerShell, adb writing to stderr (e.g.
# "device not found" while the emulator boots) would otherwise end the run.
# The script throws its own errors where it matters.
$ErrorActionPreference = "Continue"
$root = (Get-Location).Path
$sdk = "$env:LOCALAPPDATA\Android\Sdk"
$adb = "$sdk\platform-tools\adb.exe"
$serial = "emulator-$Port"
$py = "$root\backend\venv\Scripts\python.exe"
New-Item -ItemType Directory -Force $OutDir | Out-Null
$OutDir = (Resolve-Path $OutDir).Path

function Adb { & $adb -s $serial @args 2>$null }

$emu = Start-Process -FilePath "$sdk\emulator\emulator.exe" -PassThru -WindowStyle Hidden `
    -ArgumentList "-avd", $Avd, "-port", $Port, "-no-window", "-no-snapshot", "-no-audio", "-no-boot-anim", "-gpu", "swiftshader_indirect"
try {
    $started = Get-Date
    while ((Adb shell getprop sys.boot_completed) -ne "1") {
        if (((Get-Date) - $started).TotalSeconds -gt 600) { throw "$Avd didn't boot in 10 minutes" }
        Start-Sleep -Seconds 3
    }
    $boot = [int]((Get-Date) - $started).TotalSeconds
    Adb shell input keyevent 82 | Out-Null  # dismiss the lock screen
    # Always set it: the setting survives on the virtual device, so a run
    # after a large-text run would otherwise inherit the large text.
    $scale = if ($FontScale -gt 0) { $FontScale } else { 1.0 }
    Adb shell settings put system font_scale $scale | Out-Null
    # The emulator reaches this computer at 10.0.2.2 (no adb reverse, which
    # didn't survive the install), so the backend must allow that host.

    $device = [ordered]@{
        label        = $Label
        avd          = $Avd
        model        = Adb shell getprop ro.product.model
        android      = Adb shell getprop ro.build.version.release
        sdk          = Adb shell getprop ro.build.version.sdk
        screen       = ((Adb shell wm size) -join " ") -replace "Physical size: ", ""
        density      = ((Adb shell wm density) -join " ") -replace "Physical density: ", ""
        font_scale   = Adb shell settings get system font_scale
        boot_seconds = $boot
    }

    $email = $Email
    & $py "$root\scripts\device_tests\reset_test_account.py" $email | Out-File -Encoding utf8 "$OutDir\reset.txt"
    $typer = Start-Process -FilePath $py -PassThru -WindowStyle Hidden `
        -ArgumentList "$root\scripts\device_tests\type_code.py", $ServerLog, $serial, "900", $RequestLog `
        -RedirectStandardOutput "$OutDir\type_code.txt" -RedirectStandardError "$OutDir\type_code_err.txt"

    Remove-Item -Recurse -Force "$root\mobile\nurtura_app\build\e2e_screenshots" -ErrorAction SilentlyContinue
    $t0 = Get-Date
    # Windows PowerShell's module path, inherited by flutter.bat, broke
    # Flutter's own PowerShell step ("Unable to determine engine version",
    # then a failed Gradle build). Clear it for the flutter call only.
    $savedModulePath = $env:PSModulePath
    $env:PSModulePath = $null
    Push-Location "$root\mobile\nurtura_app"
    $apkPath = (Resolve-Path $Apk).Path
    cmd /c "flutter drive -d $serial --driver=test_driver/integration_test.dart --target=integration_test/app_flow_test.dart --use-application-binary=`"$apkPath`" > `"$OutDir\flutter_drive.txt`" 2> `"$OutDir\flutter_drive_err.txt`""
    $code = $LASTEXITCODE
    Pop-Location
    $env:PSModulePath = $savedModulePath
    $device.test_seconds = [int]((Get-Date) - $t0).TotalSeconds
    $device.passed = ($code -eq 0)
    $device.exit_code = $code
    if (-not $typer.HasExited) { Stop-Process -Id $typer.Id -Force }

    $shots = "$root\mobile\nurtura_app\build\e2e_screenshots"
    if (Test-Path $shots) {
        New-Item -ItemType Directory -Force "$OutDir\screenshots" | Out-Null
        Copy-Item "$shots\*.png" "$OutDir\screenshots\"
        $device.screenshots = (Get-ChildItem "$OutDir\screenshots\*.png").Count
    }
    $device | ConvertTo-Json | Out-File -Encoding utf8 "$OutDir\result.json"
    $device
} finally {
    & $adb -s $serial emu kill 2>$null | Out-Null
    Start-Sleep -Seconds 3
    if (-not $emu.HasExited) { Stop-Process -Id $emu.Id -Force -ErrorAction SilentlyContinue }
}
