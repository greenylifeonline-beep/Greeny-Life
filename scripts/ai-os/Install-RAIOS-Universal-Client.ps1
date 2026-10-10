param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("Claude","Kimi","DeepSeek","Generic")]
    [string]$Client,

    [string]$Url=$env:RAIOS_EXTERNAL_MCP_URL
)

$ErrorActionPreference="Stop"

Add-Type -AssemblyName System.Security -ErrorAction Stop

$Map=@{
    Claude=@{
        Secret="claude.dpapi"
        Env="RAIOS_CLAUDE_TOKEN"
    }
    Kimi=@{
        Secret="kimi.dpapi"
        Env="RAIOS_KIMI_TOKEN"
    }
    DeepSeek=@{
        Secret="deepseek.dpapi"
        Env="RAIOS_DEEPSEEK_TOKEN"
    }
    Generic=@{
        Secret="generic.dpapi"
        Env="RAIOS_GENERIC_TOKEN"
    }
}

if(-not $Url){
    throw "RAIOS_EXTERNAL_MCP_URL_REQUIRED"
}

if($Url -notmatch "^https://"){
    throw "RAIOS_REMOTE_ENDPOINT_MUST_USE_HTTPS"
}

$Profile=$Map[$Client]

$SecretPath=Join-Path `
    $env:USERPROFILE `
    ".raios\runtime\mcp\client-secrets\$($Profile.Secret)"

if(!(Test-Path -LiteralPath $SecretPath)){
    throw "RAIOS_CLIENT_CREDENTIAL_MISSING::$Client"
}

$b64=Get-Content -LiteralPath $SecretPath -Raw
$cipher=[Convert]::FromBase64String($b64)

$plain=[System.Security.Cryptography.ProtectedData]::Unprotect(
    $cipher,
    $null,
    [System.Security.Cryptography.DataProtectionScope]::CurrentUser
)

try{
    $token=[System.Text.Encoding]::UTF8.GetString($plain)

    [Environment]::SetEnvironmentVariable(
        "RAIOS_MCP_URL",
        $Url,
        "Process"
    )

    [Environment]::SetEnvironmentVariable(
        $Profile.Env,
        $token,
        "Process"
    )
}
finally{
    [Array]::Clear($plain,0,$plain.Length)
    Remove-Variable token -ErrorAction SilentlyContinue
}

Write-Host "RAIOS_CLIENT=$Client"
Write-Host "RAIOS_ALIAS=raios"
Write-Host "RAIOS_URL=$Url"
Write-Host "TOKEN_ENV=$($Profile.Env)"
Write-Host "RAW_TOKEN_PRINTED=False"
Write-Host "READY_FOR_CLIENT_CONFIGURATION=True"