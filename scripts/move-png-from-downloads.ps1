param (
    [Parameter(Mandatory = $true)]
    [string]$DestinationDirectory,

    [Parameter(Mandatory = $false)]
    [string]$NewFileName
)

function Main {
    $sourceDirectory = Join-Path $env:USERPROFILE "Downloads"
    $fileType = "png"

    $scriptsDirectory = Join-Path $env:USERPROFILE "Scripts"
    $scriptPath = Join-Path $scriptsDirectory "move-most-recent-file.ps1"

    if (-not (Test-Path $scriptPath -PathType Leaf)) {
        Write-Host "Script not found: $scriptPath" -ForegroundColor Red
        exit 1
    }

    if ($NewFileName) {
        & $scriptPath `
            -FileType $fileType `
            -SourceDirectory $sourceDirectory `
            -DestinationDirectory $DestinationDirectory `
            -NewFileName $NewFileName
    }
    else {
        & $scriptPath `
            -FileType $fileType `
            -SourceDirectory $sourceDirectory `
            -DestinationDirectory $DestinationDirectory
    }
}

Main
