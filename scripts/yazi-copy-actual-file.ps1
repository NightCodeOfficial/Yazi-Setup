$ErrorActionPreference = "Stop"

$TempFile = Join-Path $env:TEMP "yazi_file_to_copy.txt"

if (-not (Test-Path -LiteralPath $TempFile)) {
    Write-Host "Temp file not found:"
    Write-Host $TempFile
    exit 1
}

$FileUrl = Get-Content -LiteralPath $TempFile -Raw
$FileUrl = $FileUrl.Trim()

if ([string]::IsNullOrWhiteSpace($FileUrl)) {
    Write-Host "Temp file was empty."
    exit 1
}

if ($FileUrl -match '^file:') {
    $FilePath = ([System.Uri]$FileUrl).LocalPath
}
else {
    $FilePath = $FileUrl
}

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
