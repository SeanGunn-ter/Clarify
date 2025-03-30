<#
.SYNOPSIS
Installs Chrome Native Messaging Host for SimplifyPSU
#>

# Bypass execution policy
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force

# Configuration
$HOST_NAME = "com.clarify.server_launcher"
$LAUNCHER_SCRIPT = "launch-server.py"

# Path setup
$BASE_DIR = $PSScriptRoot
$CHROME_EXT_DIR = Join-Path $BASE_DIR "ChromeExtension"
$MANIFEST_JSON = Join-Path $CHROME_EXT_DIR "manifest.json"

# Native messaging host location
$CHROME_NM_DIR = "$env:LOCALAPPDATA\Google\Chrome\User Data\NativeMessagingHosts"
$HOST_MANIFEST = Join-Path $CHROME_NM_DIR "$HOST_NAME.json"

# Get Chrome Extension ID
function Get-ExtensionId {
    # Method 1: Get from chrome://extensions
    $extensionUrl = "chrome://extensions"
    Write-Host ""
    Write-Host "Please open $extensionUrl in Chrome and:" -ForegroundColor Yellow
    Write-Host "1. Enable 'Developer mode'" -ForegroundColor Yellow
    Write-Host "2. Find your 'Clarify' extension" -ForegroundColor Yellow
    Write-Host "3. Note the ID shown below the extension name" -ForegroundColor Yellow
    
    $extensionId = Read-Host "`nEnter the extension ID (32 lowercase letters)"
    
    # Validate format
    if ($extensionId -match "^[a-z]{32}$") {
        return $extensionId
    }
    else {
        Write-Host "ERROR: Invalid extension ID format" -ForegroundColor Red
        Write-Host "Should be 32 lowercase letters (e.g., abcdefghijklmnopqrstuvwxyzabcdef)" -ForegroundColor Yellow
        return $null
    }
}

# Verify files exist
function Test-Files {
    Write-Host ""
    Write-Host "Verifying required files..." -ForegroundColor Cyan
    
    if (-not (Test-Path (Join-Path $BASE_DIR $LAUNCHER_SCRIPT))) {
        Write-Host "ERROR: $LAUNCHER_SCRIPT not found in $BASE_DIR" -ForegroundColor Red
        return $false
    }

    if (-not (Test-Path $MANIFEST_JSON)) {
        Write-Host "ERROR: manifest.json not found in $CHROME_EXT_DIR" -ForegroundColor Red
        return $false
    }

    Write-Host "All files found" -ForegroundColor Green
    return $true
}

# Install native messaging host
function Install-NativeHost {
    param (
        [string]$extensionId
    )

    # Create directory if needed
    if (-not (Test-Path $CHROME_NM_DIR)) {
        New-Item -ItemType Directory -Path $CHROME_NM_DIR -Force | Out-Null
    }

    # Get and escape launcher path
    $launcherPath = (Get-Item (Join-Path $BASE_DIR $LAUNCHER_SCRIPT)).FullName.Replace('\', '\\')

    # Create manifest content
    $manifestContent = @"
{
    "name": "$HOST_NAME",
    "description": "Simplify PDF processor server launcher",
    "path": "$launcherPath",
    "type": "stdio",
    "allowed_origins": [
        "chrome-extension://$extensionId/"
    ]
}
"@

    # Write manifest file
    try {
        $manifestContent | Out-File -FilePath $HOST_MANIFEST -Encoding ascii -Force
        Write-Host "Native messaging host installed" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "ERROR: Failed to create manifest file" -ForegroundColor Red
        Write-Host "Details: $_" -ForegroundColor Yellow
        return $false
    }
}

# Verify installation
function Verify-Installation {
    if (Test-Path $HOST_MANIFEST) {
        try {
            $content = Get-Content $HOST_MANIFEST -Raw
            $installedManifest = $content | ConvertFrom-Json
            $expectedPath = (Get-Item (Join-Path $BASE_DIR $LAUNCHER_SCRIPT)).FullName
            
            # Normalize paths for comparison
            $installedPath = $installedManifest.path.Replace('\\', '\')
            
            if ($installedPath -eq $expectedPath) {
                Write-Host "Installation verified successfully" -ForegroundColor Green
                Write-Host "   Manifest: $HOST_MANIFEST"
                Write-Host "   Launcher: $expectedPath"
                Write-Host "   Extension ID: $($installedManifest.allowed_origins[0].Split('/')[2])"
                return $true
            }
            else {
                Write-Host "WARNING: Path comparison mismatch" -ForegroundColor Yellow
                Write-Host "   Expected: $expectedPath"
                Write-Host "   Found: $installedPath"
                return $false
            }
        }
        catch {
            Write-Host "ERROR: Failed to verify installation" -ForegroundColor Red
            Write-Host "Details: $_" -ForegroundColor Yellow
            return $false
        }
    }
    else {
        Write-Host "ERROR: Manifest file not found at $HOST_MANIFEST" -ForegroundColor Red
        return $false
    }
}

# Main execution
Write-Host ""
Write-Host "Starting SimplifyPSU Native Host Installation" -ForegroundColor Cyan
Write-Host "========================================"

# Verify files
if (-not (Test-Files)) {
    exit 1
}

# Get extension ID
$extensionId = Get-ExtensionId
if (-not $extensionId) {
    exit 1
}

# Install native host
if (-not (Install-NativeHost -extensionId $extensionId)) {
    exit 1
}

# Verify installation
Write-Host ""
Write-Host "Verifying installation..." -ForegroundColor Cyan
if (-not (Verify-Installation)) {
    exit 1
}

Write-Host ""
Write-Host "Installation completed successfully!" -ForegroundColor Green

Write-Host "Starting launch-server.py..."
Start-Process -NoNewWindow -FilePath "python" -ArgumentList "C:\Users\smgun\Downloads\SimplifyPSU\launch-server.py"
