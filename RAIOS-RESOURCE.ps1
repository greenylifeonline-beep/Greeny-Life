# RAIOS Resource Fabric read-only CLI
# JSON is authoritative. Does not mutate frozen precanonical evidence.
param(
  [Parameter(Position = 0)]
  [string]$Command = "status",
  [switch]$Human,
  [switch]$Json,
  [string]$Request
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { $Py = "python" }
$argsList = @("-m", "raios.resource_fabric", $Command)
if ($Human) { $argsList += "-Human" }
if ($Json) { $argsList += "-Json" }
if ($Request) { $argsList += @("-Request", $Request) }
$env:PYTHONPATH = Join-Path $Root "src"
& $Py @argsList
exit $LASTEXITCODE
