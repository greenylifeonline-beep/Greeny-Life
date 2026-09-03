param([string]$RuntimeRoot="$HOME\.raios\runtime\command-center",[int]$Port=8770,[string]$McpRoot="")
$ErrorActionPreference="Stop"
$Repo=(Resolve-Path(Join-Path $PSScriptRoot "..\..")).Path;$Head=(git -C $Repo rev-parse HEAD).Trim()
if(-not $McpRoot){$McpRoot=$Repo}
$McpRoot=(Resolve-Path $McpRoot).Path
if($McpRoot -ne $Repo){throw "MCP_ROOT_MUST_EQUAL_CANONICAL_REPO"}
$App=Join-Path $RuntimeRoot "app";$Logs=Join-Path $RuntimeRoot "logs";$Pkg=Join-Path $App "raios\command_center";$SearchPkg=Join-Path $App "raios\search_cortex";$ResourcePkg=Join-Path $App "raios\resource_fabric";$Mcp=Join-Path $App "raios_mcp"
$Python=Join-Path $HOME ".raios\runtime\c5\.venv\Scripts\python.exe";if(-not(Test-Path $Python)){throw "CANONICAL_C5_PYTHON_MISSING"}
$PythonWindowless=Join-Path $HOME ".raios\runtime\c5\.venv\Scripts\pythonw.exe";if(-not(Test-Path $PythonWindowless)){throw "CANONICAL_C5_PYTHONW_MISSING"}
New-Item -ItemType Directory -Force -Path $Pkg,$SearchPkg,$ResourcePkg,$Mcp,$Logs,(Join-Path $App "raios")|Out-Null
if(-not(Test-Path(Join-Path $App "raios\__init__.py"))){Set-Content(Join-Path $App "raios\__init__.py")"" -Encoding UTF8}
Copy-Item(Join-Path $Repo "src\raios\command_center\*")$Pkg -Recurse -Force
Copy-Item(Join-Path $Repo "src\raios\search_cortex\*")$SearchPkg -Recurse -Force
Copy-Item(Join-Path $Repo "src\raios\resource_fabric\*")$ResourcePkg -Recurse -Force
Copy-Item(Join-Path $Repo "scripts\ai-os\raios_mcp\*")$Mcp -Recurse -Force
$env:RAIOS_CANONICAL_REPO=$Repo;$env:RAIOS_MCP_ROOT=$McpRoot;$env:RAIOS_COMMAND_CENTER_RUNTIME=$RuntimeRoot;$env:PYTHONPATH=$App
function Start-Center([int]$Listen,[string]$Name){$out=Join-Path $Logs "$Name.out.log";$err=Join-Path $Logs "$Name.err.log";Start-Process $PythonWindowless -ArgumentList @("-m","uvicorn","raios.command_center.app:app","--app-dir",$App,"--host","127.0.0.1","--port","$Listen") -WorkingDirectory $Repo -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err -PassThru}
function Wait-Healthy([int]$Listen,[int]$ProcessId){for($i=0;$i-lt 30;$i++){Start-Sleep 1;if(-not(Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)){return $null};try{$r=Invoke-RestMethod "http://127.0.0.1:$Listen/health" -TimeoutSec 3;if($r.status-eq"ONLINE"-and$r.canonical_head-eq$Head){return $r}}catch{}};return $null}
$stagePort=$Port+1000;if(Get-NetTCPConnection -LocalPort $stagePort -State Listen -ErrorAction SilentlyContinue){throw "STAGE_PORT_IN_USE"}
$stage=Start-Center $stagePort "center.stage";$proof=Wait-Healthy $stagePort $stage.Id
if(-not$proof){Stop-Process $stage.Id -Force -ErrorAction SilentlyContinue;throw "COMMAND_CENTER_STAGE_FAILED"}
Stop-Process $stage.Id -Force;Start-Sleep -Milliseconds 400
$old=Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if($old){Stop-Process $old.OwningProcess -Force;Start-Sleep -Milliseconds 400}
$live=Start-Center $Port "center";$health=Wait-Healthy $Port $live.Id
if(-not$health){Stop-Process $live.Id -Force -ErrorAction SilentlyContinue;throw "COMMAND_CENTER_CUTOVER_FAILED"}
$listener=Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue|Select-Object -First 1
if(-not$listener){Stop-Process $live.Id -Force -ErrorAction SilentlyContinue;throw "COMMAND_CENTER_LISTENER_MISSING"}
$runtimePid=[int]$listener.OwningProcess
$manifest=[ordered]@{schema="raios.command-center-deployment.v1";canonical_head=$Head;canonical_repo=$Repo;mcp_root=$McpRoot;runtime_root=$RuntimeRoot;port=$Port;pid=$runtimePid;launcher_pid=$live.Id;deployed_at=[DateTimeOffset]::UtcNow.ToString("o");auto_canonical_mutation=$false}
$manifest|ConvertTo-Json -Depth 8|Set-Content(Join-Path $RuntimeRoot "deployment.json") -Encoding UTF8
$launcher=@"
`$env:RAIOS_CANONICAL_REPO="$Repo"
`$env:RAIOS_MCP_ROOT="$McpRoot"
`$env:RAIOS_COMMAND_CENTER_RUNTIME="$RuntimeRoot"
`$env:PYTHONPATH="$App"
`$conn=Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if(-not `$conn){
 Start-Process "$PythonWindowless" -ArgumentList @("-m","uvicorn","raios.command_center.app:app","--app-dir","$App","--host","127.0.0.1","--port","$Port") -WorkingDirectory "$Repo" -WindowStyle Hidden -RedirectStandardOutput "$Logs\center.out.log" -RedirectStandardError "$Logs\center.err.log"
 for(`$i=0;`$i-lt 20;`$i++){Start-Sleep -Milliseconds 500;try{`$h=Invoke-RestMethod "http://127.0.0.1:$Port/health" -TimeoutSec 2;if(`$h.status-eq"ONLINE"){break}}catch{}}
}
Start-Process "`$env:SystemRoot\explorer.exe" "http://127.0.0.1:$Port/"
"@
$launcherPath=Join-Path $RuntimeRoot "Open-RAIOS-Command-Center.ps1"
[IO.File]::WriteAllText($launcherPath,$launcher,[Text.UTF8Encoding]::new($false))
$desktop=[Environment]::GetFolderPath("Desktop");$shortcut=Join-Path $desktop "RAIOS Command Center.lnk";$ws=New-Object -ComObject WScript.Shell;$lnk=$ws.CreateShortcut($shortcut)
$lnk.TargetPath="$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe";$lnk.Arguments="-NoProfile -ExecutionPolicy Bypass -File `"$RuntimeRoot\Open-RAIOS-Command-Center.ps1`"";$lnk.WorkingDirectory=$RuntimeRoot;$lnk.Save()
Write-Host "COMMAND_CENTER_CANONICAL=true";Write-Host "COMMAND_CENTER_STAGE_PASS=true";Write-Host "COMMAND_CENTER_HTTP=200";Write-Host "COMMAND_CENTER_PID=$runtimePid";Write-Host "COMMAND_CENTER_LAUNCHER_PID=$($live.Id)";Write-Host "COMMAND_CENTER_HEAD=$Head";Write-Host "SHORTCUT=$shortcut"
