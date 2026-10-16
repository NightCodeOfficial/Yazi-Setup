param([Parameter(Mandatory = $true)][string]$FilePath)
$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $FilePath -PathType Leaf)) {
    Write-Host "File not found:"
    Write-Host $FilePath
    exit 1
}

$FilePath = (Resolve-Path -LiteralPath $FilePath).Path

Add-Type -AssemblyName System.Windows.Forms

$files = New-Object System.Collections.Specialized.StringCollection
[void]$files.Add($FilePath)

$data = New-Object System.Windows.Forms.DataObject
$data.SetFileDropList($files)

$dropEffect = New-Object System.IO.MemoryStream
$dropEffect.Write([byte[]](1, 0, 0, 0), 0, 4)
$data.SetData("Preferred DropEffect", $dropEffect)

for ($i = 1; $i -le 5; $i++) {
    try {
        [System.Windows.Forms.Clipboard]::SetDataObject($data, $true)
        Write-Host "Copied actual file to clipboard:"
        Write-Host $FilePath
        exit 0
    }
    catch {
        Start-Sleep -Milliseconds 200
    }
}

Write-Host "Failed to copy file to clipboard:"
Write-Host $FilePath
exit 1
