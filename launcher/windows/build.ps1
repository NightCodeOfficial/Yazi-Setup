$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$source = Join-Path $root 'src\YaziLauncher.cs'
$icon = Join-Path $root 'assets\yazi.ico'
$buildDir = Join-Path $root 'build'
$output = Join-Path $buildDir 'YaziLauncher.exe'

if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
    throw "Launcher source was not found: $source"
}
if (-not (Test-Path -LiteralPath $icon -PathType Leaf)) {
    throw "Launcher icon was not found: $icon"
}

New-Item -ItemType Directory -Path $buildDir -Force | Out-Null

$windowsRoots = @($env:WINDIR, $env:SystemRoot) |
    Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
    Select-Object -Unique

$candidates = foreach ($windowsRoot in $windowsRoots) {
    Join-Path $windowsRoot 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
    Join-Path $windowsRoot 'Microsoft.NET\Framework\v4.0.30319\csc.exe'
}

$csc = $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
if (-not $csc) {
    $command = Get-Command csc.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($command) {
        $csc = $command.Source
    }
}

if (-not $csc) {
    throw 'Could not find the Windows .NET Framework C# compiler (csc.exe). Make sure the Windows .NET Framework components are enabled, then run setup.bat again.'
}

Write-Host "Building Yazi Launcher with: $csc" -ForegroundColor Cyan
& $csc /nologo /target:winexe /platform:anycpu /optimize+ "/win32icon:$icon" "/out:$output" $source
if ($LASTEXITCODE -ne 0) {
    throw "C# compiler exited with code $LASTEXITCODE."
}

if (-not (Test-Path -LiteralPath $output -PathType Leaf)) {
    throw "Build reported success but did not create: $output"
}

Copy-Item -LiteralPath $icon -Destination (Join-Path $buildDir 'yazi.ico') -Force
Write-Host "Built: $output" -ForegroundColor Green
