param(
    [switch]$InstallYazi,
    [switch]$InstallDependencies,
    [switch]$SkipKeymap,
    [switch]$SkipLauncher,
    [switch]$DryRun,
    [ValidateSet('keep', 'choose', 'default', 'tokyo-night', 'catppuccin-mocha')]
    [string]$Theme = 'keep',
    [switch]$ChooseTheme,
    [switch]$InstallFont,
    [switch]$SkipFont,
    [string]$FontFace,
    [switch]$Test,
    [switch]$Force,
    [switch]$SkipYaziInstallPrompt,
    [switch]$SkipDependencyPrompt
)
$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'On Linux run: sh ./install.sh' }
$python = $null
foreach ($candidate in @('python.exe', 'python3.exe', 'py.exe')) {
    $command = Get-Command $candidate -ErrorAction SilentlyContinue
    if (-not $command) { continue }
    try {
        & $command.Source -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)' 2>$null
        if ($LASTEXITCODE -eq 0) { $python = $command.Source; break }
    }
    catch { continue }
}
if (-not $python) {
    throw 'Python 3.11+ is required. Run: winget install -e --id Python.Python.3.13 --source winget. Reopen your terminal, then rerun this installer.'
}
$arguments = @((Join-Path $PSScriptRoot 'setup.py'))
if ($ChooseTheme -and -not $PSBoundParameters.ContainsKey('Theme')) { $Theme = 'choose' }
$arguments += @('--theme', $Theme)
if ($InstallFont) { $arguments += '--install-font' }
if ($SkipFont) { $arguments += '--skip-font' }
if ($FontFace) { $arguments += @('--font-face', $FontFace) }
if ($InstallYazi) { $arguments += '--install-yazi' }
if ($InstallDependencies) { $arguments += '--install-dependencies' }
if ($SkipKeymap) { $arguments += '--skip-keymap' }
if ($SkipLauncher) { $arguments += '--skip-launcher' }
if ($DryRun -or $Test) { $arguments += '--dry-run' }
& $python @arguments
exit $LASTEXITCODE
