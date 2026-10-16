$ErrorActionPreference = 'Stop'

$localAppData = [Environment]::GetFolderPath([Environment+SpecialFolder]::LocalApplicationData)
$programsDir = [Environment]::GetFolderPath([Environment+SpecialFolder]::Programs)

if ([string]::IsNullOrWhiteSpace($localAppData)) {
    throw 'Windows did not provide a LocalAppData folder for the current user.'
}
if ([string]::IsNullOrWhiteSpace($programsDir)) {
    throw 'Windows did not provide a Start Menu Programs folder for the current user.'
}

$installDir = Join-Path $localAppData 'YaziLauncher'
$shortcutPath = Join-Path $programsDir 'Yazi Launcher.lnk'

if (Test-Path -LiteralPath $shortcutPath) {
    Remove-Item -LiteralPath $shortcutPath -Force
}

if (Test-Path -LiteralPath $installDir) {
    $resolvedInstall = [IO.Path]::GetFullPath($installDir)
    $expectedInstall = [IO.Path]::GetFullPath((Join-Path $localAppData 'YaziLauncher'))
    if ($resolvedInstall -ne $expectedInstall -or (Get-Item -LiteralPath $installDir).Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw 'Refusing to remove an unexpected path or linked launcher directory.'
    }
    Remove-Item -LiteralPath $installDir -Recurse -Force
}

Write-Host 'Yazi Launcher files and Start Menu shortcut were removed.' -ForegroundColor Green
Write-Host 'If it is pinned to the taskbar, right-click the pinned icon and choose Unpin from taskbar.'
