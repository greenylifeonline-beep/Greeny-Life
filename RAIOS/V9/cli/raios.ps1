param(
    [Parameter(Position=0)]
    [string]$Command = "context",

    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$Remaining
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot

$Python = Get-Command python -ErrorAction Stop

& $Python.Source `
    "$PSScriptRoot\raios_v9.py" `
    $Command `
    @Remaining

exit $LASTEXITCODE
