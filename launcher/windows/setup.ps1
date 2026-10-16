param([switch]$NoLaunch)
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$buildScript = Join-Path $root 'build.ps1'

if (-not (Test-Path -LiteralPath $buildScript -PathType Leaf)) {
    throw "Build script was not found: $buildScript"
}

$localAppData = [Environment]::GetFolderPath([Environment+SpecialFolder]::LocalApplicationData)
$userProfile = [Environment]::GetFolderPath([Environment+SpecialFolder]::UserProfile)
$programsDir = [Environment]::GetFolderPath([Environment+SpecialFolder]::Programs)

if ([string]::IsNullOrWhiteSpace($localAppData)) {
    throw 'Windows did not provide a LocalAppData folder for the current user.'
}
if ([string]::IsNullOrWhiteSpace($userProfile)) {
    throw 'Windows did not provide a user-profile folder for the current user.'
}
if ([string]::IsNullOrWhiteSpace($programsDir)) {
    throw 'Windows did not provide a Start Menu Programs folder for the current user.'
}

& $buildScript

$buildDir = Join-Path $root 'build'
$builtExe = Join-Path $buildDir 'YaziLauncher.exe'
$builtIcon = Join-Path $buildDir 'yazi.ico'

if (-not (Test-Path -LiteralPath $builtExe -PathType Leaf)) {
    throw "Built launcher was not found: $builtExe"
}
if (-not (Test-Path -LiteralPath $builtIcon -PathType Leaf)) {
    throw "Built launcher icon was not found: $builtIcon"
}

$installDir = Join-Path $localAppData 'YaziLauncher'
$installedExe = Join-Path $installDir 'YaziLauncher.exe'
$installedIcon = Join-Path $installDir 'yazi.ico'

New-Item -ItemType Directory -Path $installDir -Force | Out-Null
Copy-Item -LiteralPath $builtExe -Destination $installedExe -Force
Copy-Item -LiteralPath $builtIcon -Destination $installedIcon -Force

$shortcutPath = Join-Path $programsDir 'Yazi Launcher.lnk'

$wshShell = $null
$shortcut = $null
try {
    $wshShell = New-Object -ComObject WScript.Shell
    $shortcut = $wshShell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $installedExe
    $shortcut.WorkingDirectory = $userProfile
    $shortcut.IconLocation = "$installedIcon,0"
    $shortcut.Description = 'Launch Yazi in its own Windows Terminal taskbar group.'
    $shortcut.Save()
}
finally {
    if ($shortcut) {
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($shortcut)
    }
    if ($wshShell) {
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($wshShell)
    }
}

& $installedExe --set-shortcut-appid $shortcutPath
if ($LASTEXITCODE -ne 0) {
    throw "The launcher was built, but tagging the Start Menu shortcut with its AppUserModelID failed (exit code $LASTEXITCODE)."
}

Write-Host ''
Write-Host 'Yazi Launcher is installed.' -ForegroundColor Green
Write-Host 'A Start Menu shortcut named "Yazi Launcher" was created.'
Write-Host 'Pin that shortcut to the taskbar, or pin the Yazi taskbar button after it opens.'
Write-Host ''
if (-not $NoLaunch) {
    Write-Host 'Launching Yazi once now so you can verify the separate taskbar group...' -ForegroundColor Cyan
    Start-Process -FilePath $installedExe -WindowStyle Hidden
}
