param(
    [string]$Repo='C:\Users\Ghanam\Documents\Codex\Greeny-Life',
    [string]$Profile='raios-native',
    [string]$Alias='raios'
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Security

$Root='C:\Users\Ghanam\.raios\runtime\mcp-tunnel'
$Client=Join-Path $Root 'bin\tunnel-client.exe'
$ProfileDir=Join-Path $Root 'profiles'
$MachineSecret=Join-Path $Root 'secrets\control-plane-api-key.machine.dpapi'
$TokenStore=Join-Path $Repo '.ai-os\mcp\tokens.local.json'
$HealthFile='C:\Users\Ghanam\.local\state\tunnel-client\health\raios-native.url'
$EvidenceRoot=Join-Path $Root 'diagnostics'
$ReceiptPath=Join-Path $EvidenceRoot 'native-tunnel-inspection.json'

function Write-JsonAtomic([string]$Path,$Value){
    [IO.Directory]::CreateDirectory((Split-Path -Parent $Path))|Out-Null
    $tmp=$Path+'.tmp-'+[guid]::NewGuid().ToString('N')
    $Value|ConvertTo-Json -Depth 20|Set-Content -LiteralPath $tmp -Encoding UTF8
    Move-Item -LiteralPath $tmp -Destination $Path -Force
}

function Sha256Text([string]$Text){
    $sha=[Security.Cryptography.SHA256]::Create()
    try{
        $bytes=[Text.Encoding]::UTF8.GetBytes($Text)
        return ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-','').ToLowerInvariant()
    }finally{$sha.Dispose()}
}

function Get-ProfilePath {
    foreach($candidate in @(
        (Join-Path $ProfileDir ($Profile+'.yaml')),
        (Join-Path $ProfileDir ($Profile+'.yml')),
        (Join-Path $ProfileDir $Profile)
    )){
        if(Test-Path -LiteralPath $candidate){return $candidate}
    }
    return $null
}

function Match-YamlScalar([string]$Text,[string]$Name){
    $pattern='(?im)^\s*'+[regex]::Escape($Name)+'\s*:\s*["'']?([^#\r\n"'']+)["'']?\s*(?:#.*)?$'
    $m=[regex]::Match($Text,$pattern)
    if(-not $m.Success){return $null}
    return $m.Groups[1].Value.Trim()
}

function Invoke-CapturedProcess([string]$File,[string[]]$Arguments,[int]$TimeoutSeconds=30){
    $psi=[Diagnostics.ProcessStartInfo]::new()
    $psi.FileName=$File
    $psi.UseShellExecute=$false
    $psi.CreateNoWindow=$true
    $psi.RedirectStandardOutput=$true
    $psi.RedirectStandardError=$true
    $psi.WorkingDirectory=$Root
    $quoted=[System.Collections.Generic.List[string]]::new()
    foreach($arg in $Arguments){
        $quoted.Add('"'+([string]$arg).Replace('"','\"')+'"')
    }
    $psi.Arguments=($quoted -join ' ')
    $p=[Diagnostics.Process]::new()
    $p.StartInfo=$psi
    try{
        if(-not $p.Start()){throw 'PROCESS_START_FAILED'}
        $stdout=$p.StandardOutput.ReadToEndAsync()
        $stderr=$p.StandardError.ReadToEndAsync()
        if(-not $p.WaitForExit([Math]::Max(1,$TimeoutSeconds)*1000)){
            try{$p.Kill()}catch{}
            return [pscustomobject]@{ok=$false;exit_code=$null;timed_out=$true;stdout='';stderr='TIMEOUT'}
        }
        $out=if($stdout.Wait(3000)){$stdout.Result}else{''}
        $err=if($stderr.Wait(3000)){$stderr.Result}else{''}
        return [pscustomobject]@{ok=($p.ExitCode -eq 0);exit_code=$p.ExitCode;timed_out=$false;stdout=$out;stderr=$err}
    }finally{$p.Dispose()}
}

function Sanitize-Text([string]$Text){
    if([string]::IsNullOrEmpty($Text)){return ''}
    $s=$Text
    $s=[regex]::Replace($s,'(?i)Bearer\s+[A-Za-z0-9._~+/=-]+','Bearer <redacted>')
    $s=[regex]::Replace($s,'(?i)\bsk-[A-Za-z0-9._-]{8,}\b','<redacted-key>')
    $s=[regex]::Replace($s,'(?im)^(\s*(?:api_key|token|secret|authorization)\s*[:=]\s*).+$','$1<redacted>')
    if($s.Length -gt 12000){$s=$s.Substring(0,12000)+[Environment]::NewLine+'<TRUNCATED>'}
    return $s
}

function Probe-Http([string]$Url,[int]$TimeoutSec=4){
    try{
        $r=Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec $TimeoutSec
        $body=[string]$r.Content
        return [pscustomobject]@{
            ok=($r.StatusCode -ge 200 -and $r.StatusCode -lt 300)
            status_code=[int]$r.StatusCode
            body_sha256=$(if($body){Sha256Text $body}else{$null})
        }
    }catch{
        $code=$null
        try{$code=[int]$_.Exception.Response.StatusCode}catch{}
        return [pscustomobject]@{
            ok=$false
            status_code=$code
            error_type=$_.Exception.GetType().Name
        }
    }
}

$plainBytes=$null
$cipher=$null
$apiKey=$null
$delegateToken=$null
$oldEnv=@{}
foreach($n in @('CONTROL_PLANE_API_KEY','RAIOS_MCP_TOKEN','RAIOS_MCP_ACTOR','MCP_EXTRA_HEADERS','MCP_DISCOVERY_EXTRA_HEADERS')){
    $oldEnv[$n]=[Environment]::GetEnvironmentVariable($n,'Process')
}

try{
    $profilePath=Get-ProfilePath
    if(-not $profilePath){throw 'RAIOS_NATIVE_PROFILE_MISSING'}
    if(-not(Test-Path -LiteralPath $Client)){throw 'TUNNEL_CLIENT_MISSING'}
    if(-not(Test-Path -LiteralPath $MachineSecret)){throw 'MACHINE_DPAPI_SECRET_MISSING'}
    if(-not(Test-Path -LiteralPath $TokenStore)){throw 'RAIOS_TOKEN_STORE_MISSING'}

    $profileText=[IO.File]::ReadAllText($profilePath)
    $tunnelId=Match-YamlScalar $profileText 'tunnel_id'
    $baseUrl=Match-YamlScalar $profileText 'base_url'
    $urlPath=Match-YamlScalar $profileText 'url_path'
    $serverUrl=Match-YamlScalar $profileText 'server_url'

    if([string]::IsNullOrWhiteSpace($tunnelId)){throw 'PROFILE_TUNNEL_ID_MISSING'}
    $tunnelIdValid=[bool]($tunnelId -match '^tunnel_[0-9a-f]{32}$')
    $tunnelFingerprint=Sha256Text $tunnelId
    $tunnelSuffix=if($tunnelId.Length -ge 8){$tunnelId.Substring($tunnelId.Length-8)}else{$tunnelId}

    $cipher=[IO.File]::ReadAllBytes($MachineSecret)
    $plainBytes=[Security.Cryptography.ProtectedData]::Unprotect(
        $cipher,$null,[Security.Cryptography.DataProtectionScope]::LocalMachine
    )
    $apiKey=[Text.Encoding]::UTF8.GetString($plainBytes)
    if([string]::IsNullOrWhiteSpace($apiKey)){throw 'MACHINE_DPAPI_DECRYPT_EMPTY'}

    $tokens=Get-Content -LiteralPath $TokenStore -Raw|ConvertFrom-Json
    $delegate=@($tokens.actors|Where-Object{[string]$_.actor_id -eq 'CHATGPT_NATIVE_DELEGATE'})|Select-Object -First 1
    if(-not $delegate -or [string]::IsNullOrWhiteSpace([string]$delegate.token)){
        throw 'CHATGPT_NATIVE_DELEGATE_TOKEN_GRANT_MISSING'
    }
    $delegateToken=[string]$delegate.token

    [Environment]::SetEnvironmentVariable('CONTROL_PLANE_API_KEY',$apiKey,'Process')
    [Environment]::SetEnvironmentVariable('RAIOS_MCP_TOKEN',$delegateToken,'Process')
    [Environment]::SetEnvironmentVariable('RAIOS_MCP_ACTOR','CHATGPT_NATIVE_DELEGATE','Process')
    [Environment]::SetEnvironmentVariable('MCP_EXTRA_HEADERS',('X-RAIOS-TOKEN: '+$delegateToken),'Process')
    [Environment]::SetEnvironmentVariable('MCP_DISCOVERY_EXTRA_HEADERS',('X-RAIOS-TOKEN: '+$delegateToken),'Process')

    $mcp=$null
    try{$mcp=Invoke-RestMethod -Uri 'http://127.0.0.1:8788/health' -TimeoutSec 5}catch{}
    $mcpReady=[bool](
        $mcp -and $mcp.ok -eq $true -and [int]$mcp.tool_count -eq 9 -and
        $mcp.execute_scoped_task -eq $true -and $mcp.second_gateway -eq $false -and
        $mcp.duplicate_mcp -eq $false -and $mcp.raw_shell -eq $false
    )

    $adminBase=$null
    if(Test-Path -LiteralPath $HealthFile){
        try{$adminBase=(Get-Content -LiteralPath $HealthFile -Raw).Trim()}catch{}
    }
    $adminBaseValid=[bool]($adminBase -match '^http://127\.0\.0\.1:\d+$')
    $readyz=if($adminBaseValid){Probe-Http ($adminBase+'/readyz')}else{[pscustomobject]@{ok=$false;status_code=$null;error_type='ADMIN_URL_INVALID'}}
    $healthDetails=if($adminBaseValid){Probe-Http ($adminBase+'/health?details=true')}else{[pscustomobject]@{ok=$false;status_code=$null;error_type='ADMIN_URL_INVALID'}}
    $mcpHealth=if($adminBaseValid){Probe-Http ($adminBase+'/health/mcp')}else{[pscustomobject]@{ok=$false;status_code=$null;error_type='ADMIN_URL_INVALID'}}

    $doctor=Invoke-CapturedProcess $Client @('doctor','--profile-dir',$ProfileDir,'--profile',$Profile,'--explain') 45
    $doctorOut=Sanitize-Text ($doctor.stdout+[Environment]::NewLine+$doctor.stderr)

    $remote=Invoke-CapturedProcess $Client @('admin','--json','tunnels','get',$tunnelId) 45
    $remoteObj=$null
    if($remote.ok){
        try{$remoteObj=$remote.stdout|ConvertFrom-Json}catch{}
    }

    $remoteTunnelId=$null
    $remoteName=$null
    $remoteStatus=$null
    $orgCount=$null
    $workspaceCount=$null
    if($remoteObj){
        foreach($field in @('id','tunnel_id')){
            if($remoteObj.PSObject.Properties[$field]){$remoteTunnelId=[string]$remoteObj.$field;break}
        }
        if($remoteObj.PSObject.Properties['name']){$remoteName=[string]$remoteObj.name}
        if($remoteObj.PSObject.Properties['status']){$remoteStatus=[string]$remoteObj.status}
        if($remoteObj.PSObject.Properties['organization_ids']){$orgCount=@($remoteObj.organization_ids).Count}
        if($remoteObj.PSObject.Properties['workspace_ids']){$workspaceCount=@($remoteObj.workspace_ids).Count}
    }

    $bindingOk=[bool]($serverUrl -eq 'http://127.0.0.1:8788/mcp')
    $remoteIdMatches=[bool]($remoteTunnelId -and $remoteTunnelId -eq $tunnelId)

    $blockers=[System.Collections.Generic.List[string]]::new()
    if(-not $tunnelIdValid){$blockers.Add('PROFILE_TUNNEL_ID_INVALID')}
    if(-not $bindingOk){$blockers.Add('PROFILE_MCP_UPSTREAM_MISMATCH')}
    if(-not $mcpReady){$blockers.Add('LOCAL_UNIVERSAL_MCP_NOT_READY')}
    if(-not $readyz.ok){$blockers.Add('TUNNEL_READYZ_NOT_READY')}
    if(-not $doctor.ok){$blockers.Add('TUNNEL_DOCTOR_FAILED')}
    if(-not $remote.ok){$blockers.Add('CONTROL_PLANE_TUNNEL_GET_FAILED')}
    elseif(-not $remoteIdMatches){$blockers.Add('CONTROL_PLANE_TUNNEL_ID_MISMATCH')}

    $result=if($blockers.Count -eq 0){'PASS'}else{'BLOCKED'}
    $receipt=[ordered]@{
        schema='raios.native-tunnel-inspection.v1'
        observed_at=[DateTimeOffset]::UtcNow.ToString('o')
        result=$result
        mutation_performed=$false
        profile=[ordered]@{
            name=$Profile
            path=$profilePath
            sha256=(Get-FileHash -LiteralPath $profilePath -Algorithm SHA256).Hash.ToLowerInvariant()
            tunnel_id_valid=$tunnelIdValid
            tunnel_id_sha256=$tunnelFingerprint
            tunnel_id_suffix=$tunnelSuffix
            control_plane_base_url=$baseUrl
            control_plane_url_path=$urlPath
            mcp_server_url=$serverUrl
            mcp_upstream_matches_canonical=$bindingOk
        }
        local_mcp=[ordered]@{
            ready=$mcpReady
            service=$(if($mcp){[string]$mcp.service}else{$null})
            head=$(if($mcp){[string]$mcp.head}else{$null})
            head_source=$(if($mcp){[string]$mcp.head_source}else{$null})
            tool_count=$(if($mcp){[int]$mcp.tool_count}else{0})
            execute_scoped_task=$(if($mcp){[bool]$mcp.execute_scoped_task}else{$false})
            second_gateway=$(if($mcp){[bool]$mcp.second_gateway}else{$null})
            duplicate_mcp=$(if($mcp){[bool]$mcp.duplicate_mcp}else{$null})
            raw_shell=$(if($mcp){[bool]$mcp.raw_shell}else{$null})
        }
        tunnel_admin=[ordered]@{
            health_url=$adminBase
            readyz=$readyz
            health_details=$healthDetails
            mcp_health=$mcpHealth
        }
        doctor=[ordered]@{
            ok=[bool]$doctor.ok
            exit_code=$doctor.exit_code
            timed_out=[bool]$doctor.timed_out
            sanitized_output=$doctorOut
        }
        control_plane=[ordered]@{
            tunnel_get_ok=[bool]$remote.ok
            exit_code=$remote.exit_code
            tunnel_id_matches_profile=$remoteIdMatches
            name=$remoteName
            status=$remoteStatus
            organization_scope_count=$orgCount
            workspace_scope_count=$workspaceCount
            error=$(if($remote.ok){$null}else{Sanitize-Text ($remote.stderr+[Environment]::NewLine+$remote.stdout)})
        }
        connector_expectation=[ordered]@{
            alias=$Alias
            required_tunnel_id_sha256=$tunnelFingerprint
            required_tunnel_id_suffix=$tunnelSuffix
            next_action=$(if($blockers.Count -eq 0){'VERIFY_CHATGPT_CONNECTOR_SELECTS_THIS_TUNNEL_ID'}else{'FIX_RUNTIME_OR_CONTROL_PLANE_BLOCKERS_FIRST'})
        }
        blockers=@($blockers)
    }

    Write-JsonAtomic $ReceiptPath $receipt
    $receipt|ConvertTo-Json -Depth 20
    if($result -ne 'PASS'){exit 2}
    exit 0
}
finally{
    foreach($n in @($oldEnv.Keys)){
        [Environment]::SetEnvironmentVariable($n,$oldEnv[$n],'Process')
    }
    if($plainBytes){[Array]::Clear($plainBytes,0,$plainBytes.Length)}
    if($cipher){[Array]::Clear($cipher,0,$cipher.Length)}
    $apiKey=$null
    $delegateToken=$null
}
