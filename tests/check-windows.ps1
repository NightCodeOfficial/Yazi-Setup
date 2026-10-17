$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$tempDir = Join-Path ([IO.Path]::GetTempPath()) ('yazi-check-' + [Guid]::NewGuid().ToString('N'))
$originalProfile = $env:USERPROFILE
$originalLocation = Get-Location
try {
    New-Item -ItemType Directory -Path $tempDir | Out-Null
    $env:USERPROFILE = $tempDir
    $downloads = Join-Path $tempDir 'Downloads'
    $destination = Join-Path $tempDir 'destination [test]'
    $templates = Join-Path $tempDir 'User-Templates'
    foreach ($directory in @($downloads, $destination, $templates)) {
        New-Item -ItemType Directory -Path $directory | Out-Null
    }
    $source = Join-Path $downloads 'image [1].png'
    [IO.File]::WriteAllText($source, 'png test')
    & (Join-Path $root 'scripts\move-png-from-downloads.ps1') -DestinationDirectory $destination
    $moved = Join-Path $destination 'image [1].png'
    if (-not (Test-Path -LiteralPath $moved) -or (Test-Path -LiteralPath $source)) {
        throw 'PNG move helper failed with bracket characters in paths.'
    }
    [IO.File]::WriteAllText((Join-Path $templates 'blank.docx'), 'template')
    Set-Location -LiteralPath $destination
    function Read-Host { return 'report.v2 [1]' }
    function Start-Sleep { }
    & (Join-Path $root 'scripts\new-office-file.ps1') -Type docx
    if (-not (Test-Path -LiteralPath (Join-Path $destination 'report.v2 [1].docx'))) {
        throw 'Office helper failed to preserve dots and brackets in filenames.'
    }

    $assembly = [Reflection.Assembly]::LoadFile((Join-Path $root 'launcher\windows\build\YaziLauncher.exe'))
    $program = $assembly.GetType('YaziLauncher.Program')
    $quote = $program.GetMethod('Quote', [Reflection.BindingFlags]'Static,NonPublic')
    if ($quote.Invoke($null, @('C:\')) -ne '"C:\\"') {
        throw 'Launcher quoting failed for a trailing backslash.'
    }
    if ($quote.Invoke($null, @('a"b')) -ne '"a\"b"') {
        throw 'Launcher quoting failed for an embedded quote.'
    }
    Write-Host 'Windows helper and launcher checks passed.'
}
finally {
    Set-Location $originalLocation
    $env:USERPROFILE = $originalProfile
    # This exact, newly-created test directory is the only cleanup target.
    if ([IO.Path]::GetFullPath($tempDir).StartsWith([IO.Path]::GetFullPath([IO.Path]::GetTempPath()), [StringComparison]::OrdinalIgnoreCase)) {
        Remove-Item -LiteralPath $tempDir -Recurse -Force
    }
}
