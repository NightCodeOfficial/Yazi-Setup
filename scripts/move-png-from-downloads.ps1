param(
    [Parameter(Mandatory = $true)][string]$DestinationDirectory,
    [string]$NewFileName
)
$ErrorActionPreference = 'Stop'
$scriptPath = Join-Path $PSScriptRoot 'move-most-recent-file.ps1'
if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) {
    throw "Script not found: $scriptPath"
}
$parameters = @{
    FileType = 'png'
    SourceDirectory = Join-Path $env:USERPROFILE 'Downloads'
    DestinationDirectory = $DestinationDirectory
}
if ($NewFileName) { $parameters.NewFileName = $NewFileName }
& $scriptPath @parameters
