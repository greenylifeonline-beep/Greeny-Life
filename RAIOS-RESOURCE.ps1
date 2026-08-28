# RAIOS Resource Fabric CLI
# JSON is authoritative. Placement is executable. Dispatch plans are dry-run.
param(
  [Parameter(Position = 0)]
  [string]$Command = "status",
  [switch]$Human,
  [switch]$Json,
  [string]$Request,
  [string]$Workload,
  [string]$Authority,
  [switch]$Paid,
  [switch]$DryRun,
  [switch]$NoProbe
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { $Py = "python" }
$argsList = @("-m", "raios.resource_fabric", $Command)
if ($Human) { $argsList += "-Human" }
if ($Json) { $argsList += "-Json" }
if ($Request) { $argsList += @("-Request", $Request) }
if ($Workload) { $argsList += @("-Workload", $Workload) }
if ($Authority) { $argsList += @("-Authority", $Authority) }
if ($Paid) { $argsList += "-Paid" }
if ($DryRun) { $argsList += "-DryRun" }
if ($NoProbe) { $argsList += "--no-probe" }
$env:PYTHONPATH = Join-Path $Root "src"
& $Py @argsList
exit $LASTEXITCODE
