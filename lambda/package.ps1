# Package Lambda function for deployment
# Usage: .\package.ps1
# All Lambda-related files are now in this folder, so packaging is simple!

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Split-Path -Parent $ScriptDir
$ZipFile = Join-Path $BackendDir "lambda.zip"

Write-Host "Packaging Lambda function from $ScriptDir..." -ForegroundColor Yellow

# Remove old zip if exists
if (Test-Path $ZipFile) {
    Remove-Item -Force $ZipFile
}

# Create zip file directly from lambda folder
# Exclude packaging scripts and README from the zip
Set-Location $ScriptDir
$filesToZip = @(
    "lambda_ses_scheduler.py",
    "finance_analyzer_lib"
)
Compress-Archive -Path $filesToZip -DestinationPath $ZipFile -Force
Set-Location $BackendDir

$ZipSize = (Get-Item $ZipFile).Length / 1KB
Write-Host "✓ Lambda package created: $ZipFile" -ForegroundColor Green
Write-Host "  Size: $([math]::Round($ZipSize, 2)) KB" -ForegroundColor Gray
Write-Host ""
Write-Host "Package contents:" -ForegroundColor Cyan
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::OpenRead($ZipFile)
$zip.Entries | Where-Object { $_.Name -like "*lambda_ses_scheduler*" -or $_.FullName -like "*finance_analyzer_lib*" } | Select-Object -First 10 | ForEach-Object { Write-Host "  $($_.FullName)" }
$zip.Dispose()

