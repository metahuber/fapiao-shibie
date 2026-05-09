param([string]$Version)

$iscc = $null
$paths = @(
    "C:\Program Files (x86)\Inno Setup 6\iscc.exe",
    "C:\Program Files\Inno Setup 6\iscc.exe"
)
foreach ($p in $paths) {
    if (Test-Path $p) { $iscc = $p; break }
}
if (-not $iscc) { $iscc = "iscc" }

Write-Host "iscc: $iscc"
& $iscc installer.iss /Q "/DMyAppVersion=$Version"
exit $LastExitCode
