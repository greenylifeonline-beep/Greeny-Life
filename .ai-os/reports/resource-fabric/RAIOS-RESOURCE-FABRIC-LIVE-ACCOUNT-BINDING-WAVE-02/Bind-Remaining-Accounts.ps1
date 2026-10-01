# RAIOS remaining account bind. No GPU. No VM. Do not paste tokens into chat.
# Run ONE step per PowerShell window. After each browser login, wait until the prompt returns.

$ErrorActionPreference = "Stop"

function Refresh-Path {
    $machine = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $user = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machine;$user"
}

function Find-Gcloud {
    $cmd = Get-Command gcloud -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $cands = @(
        "${env:ProgramFiles(x86)}\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        "$env:ProgramFiles\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        "$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        "C:\gcloud-sdk\google-cloud-sdk\bin\gcloud.cmd"
    )
    foreach ($p in $cands) {
        if (Test-Path -LiteralPath $p) { return $p }
    }
    return $null
}

$step = $args[0]
if (-not $step) {
    Write-Host "Usage: .\Bind-Remaining-Accounts.ps1 <Lightning|OracleInstall|OracleLogin|GcloudInstall|GcloudLogin>"
    Write-Host "Already in RAIOS: Hugging Face, Modal, Kaggle, Lightning (credentials on disk)."
    Write-Host "Still AUTH_REQUIRED until browser login: Oracle, Colab/Google ADC."
    Write-Host "gcloud is not on PATH until Cloud SDK is installed. Do not run gcloud before GcloudInstall."
    exit 2
}

Refresh-Path

switch ($step) {
    "Lightning" {
        if (-not (Get-Command lightning -ErrorAction SilentlyContinue)) {
            python -m pip install -U lightning-sdk
            Refresh-Path
        }
        Write-Host "Browser will open. Sign in, then return here until login finishes."
        lightning login
    }
    "OracleInstall" {
        & "$PSScriptRoot\Install-Remaining-CLIs.ps1"
        if (-not (Test-Path "X:\")) { subst X: C:\o }
        $env:Path = "X:\Scripts;" + $env:Path
        if (-not (Get-Command oci -ErrorAction SilentlyContinue)) {
            Write-Host "oci still not on PATH. Close this window and open a new PowerShell, then run OracleLogin."
            exit 1
        }
        Write-Host "oci CLI installed. Next: .\Bind-Remaining-Accounts.ps1 OracleLogin"
    }
    "OracleLogin" {
        if (-not (Test-Path "X:\")) {
            if (Test-Path "C:\o") { subst X: C:\o }
        }
        $env:Path = "X:\Scripts;" + $env:Path
        Refresh-Path
        if (-not (Get-Command oci -ErrorAction SilentlyContinue)) {
            Write-Host "oci not found. Run OracleInstall first."
            exit 1
        }
        Write-Host "Browser will open. Sign in to Oracle. Do not create a VM."
        oci session authenticate
    }
    "GcloudInstall" {
        winget install -e --id Google.CloudSDK --accept-package-agreements --accept-source-agreements
        Refresh-Path
        $g = Find-Gcloud
        if (-not $g) {
            Write-Host "Cloud SDK installed or still installing. Close PowerShell, open a new one, then run GcloudLogin."
            exit 1
        }
        Write-Host "gcloud at $g. Next: .\Bind-Remaining-Accounts.ps1 GcloudLogin"
    }
    "GcloudLogin" {
        Refresh-Path
        $g = Find-Gcloud
        if (-not $g) {
            Write-Host "gcloud not found. Run GcloudInstall first, then open a NEW PowerShell."
            exit 1
        }
        Write-Host "Browser will open for Google ADC. Do not start a Colab GPU."
        & $g auth application-default login
    }
    default {
        Write-Host "Unknown step: $step"
        exit 2
    }
}
