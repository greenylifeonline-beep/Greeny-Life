# Google ADC for RAIOS Colab/Google bind. NOT a Colab GPU runtime.
$ErrorActionPreference = "Stop"
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
$env:CLOUDSDK_PYTHON = "C:\Users\Ghanam\AppData\Local\Programs\Python\Python312\python.exe"
$machine = [Environment]::GetEnvironmentVariable("Path", "Machine")
$user = [Environment]::GetEnvironmentVariable("Path", "User")
$env:Path = "$machine;$user;$env:Path"
$g = Find-Gcloud
if (-not $g) { throw "gcloud not found at C:\gcloud-sdk\google-cloud-sdk\bin\gcloud.cmd" }
Write-Host "Using $g"
Write-Host "CLOUDSDK_PYTHON=$env:CLOUDSDK_PYTHON"
Write-Host "Browser will open for Application Default Credentials."
Write-Host "Do not start a Colab GPU. Do not create a billed VM."
& $g auth application-default login
Write-Host "GCLOUD_ADC_EXIT=$LASTEXITCODE"
