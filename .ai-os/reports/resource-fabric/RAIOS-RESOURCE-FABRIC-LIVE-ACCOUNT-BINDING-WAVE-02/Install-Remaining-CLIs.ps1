# Install Oracle CLI (short drive to dodge Windows MAX_PATH) and Google Cloud SDK.
# No VM. No GPU. No secrets.
$ErrorActionPreference = "Stop"
$root = "C:\o"
New-Item -ItemType Directory -Force -Path $root | Out-Null

function Ensure-Subst {
    if (-not (Test-Path "X:\")) {
        subst X: $root
    }
    if (-not (Test-Path "X:\")) {
        throw "subst X: failed"
    }
}

function Install-OciCli {
    Ensure-Subst
    Write-Host "Installing oci-cli into X:\ (short path; Windows Long Paths is off)"
    $pipArgs = @(
        "-m", "pip", "install", "oci-cli",
        "--prefix", "X:\",
        "--no-deps",
        "--no-warn-script-location",
        "--default-timeout", "300",
        "--retries", "5"
    )
    & python @pipArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Prefix install failed. Stripping help-text files from the wheel and retrying."
        $wd = Join-Path $root "wheels"
        New-Item -ItemType Directory -Force -Path $wd | Out-Null
        & python -m pip download oci-cli -d $wd --default-timeout 300 --retries 5
        $wheel = Get-ChildItem -LiteralPath $wd -Filter "oci_cli-*.whl" | Select-Object -First 1
        if (-not $wheel) { throw "oci-cli wheel not downloaded" }
        $stripDir = Join-Path $root "strip"
        if (Test-Path $stripDir) { Remove-Item -Recurse -Force $stripDir }
        New-Item -ItemType Directory -Force -Path $stripDir | Out-Null
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        [System.IO.Compression.ZipFile]::ExtractToDirectory($wheel.FullName, $stripDir)
        $help = Join-Path $stripDir "oci_cli\help_text_producer\data_files"
        if (Test-Path $help) { Remove-Item -Recurse -Force $help }
        $fixed = Join-Path $wd ("stripped-" + $wheel.Name)
        if (Test-Path $fixed) { Remove-Item -Force $fixed }
        [System.IO.Compression.ZipFile]::CreateFromDirectory($stripDir, $fixed)
        & python -m pip install $fixed --prefix X:\ --no-deps --no-warn-script-location
        if ($LASTEXITCODE -ne 0) { throw "stripped oci-cli install failed" }
    }
    $oci = "X:\Scripts\oci.exe"
    if (-not (Test-Path $oci)) { throw "oci.exe missing after install: $oci" }
    Write-Host "OCI_OK $oci"
}

function Install-Gcloud {
    $cands = @(
        "${env:ProgramFiles(x86)}\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        "$env:ProgramFiles\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        "$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        "C:\gcloud-sdk\google-cloud-sdk\bin\gcloud.cmd"
    )
    foreach ($p in $cands) {
        if (Test-Path -LiteralPath $p) {
            Write-Host "GCLOUD_ALREADY $p"
            return $p
        }
    }
    Write-Host "Installing Google Cloud SDK via winget (ADC only; no Colab GPU)"
    & winget install -e --id Google.CloudSDK --accept-package-agreements --accept-source-agreements --disable-interactivity
    foreach ($p in $cands) {
        if (Test-Path -LiteralPath $p) {
            Write-Host "GCLOUD_OK $p"
            return $p
        }
    }
    Write-Host "winget did not place gcloud. Downloading official installer to C:\o"
    $exe = Join-Path $root "GoogleCloudSDKInstaller.exe"
    Invoke-WebRequest -Uri "https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe" -OutFile $exe
    $dest = "C:\gcloud-sdk"
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    Start-Process -FilePath $exe -ArgumentList "/S","/D=$dest" -Wait
    $g = Join-Path $dest "google-cloud-sdk\bin\gcloud.cmd"
    if (-not (Test-Path $g)) { throw "gcloud.cmd missing after installer" }
    Write-Host "GCLOUD_OK $g"
    return $g
}

Install-OciCli
Install-Gcloud
Write-Host "INSTALL_DONE"
Write-Host "Next (new PowerShell, one window each):"
Write-Host "  1) .\Run-Oracle-Login.ps1"
Write-Host "  2) .\Run-Gcloud-ADC-Login.ps1"
Write-Host "Lightning: skip if credentials.json already exists."
