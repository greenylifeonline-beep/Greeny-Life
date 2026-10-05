# Shared contract for local ownership checks and Native tunnel readiness.
# Does not start processes, discover providers, or grant permissions.
function Test-RaiosMcpHealth {
 param($Health,[string]$PolicyPath)
 try {
  $policy=Get-Content -LiteralPath $PolicyPath -Raw -Encoding UTF8|ConvertFrom-Json
  $expected=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
  foreach($name in (@($policy.v1_tools)+@($policy.execution_tools))){
   if($name -isnot [string] -or [string]::IsNullOrWhiteSpace($name) -or -not $expected.Add($name)){return $false}
  }
  if(-not $expected.Contains('execute_scoped_task')){return $false}
  $actual=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
  foreach($name in @($Health.tools)){
   if($name -isnot [string] -or -not $actual.Add($name)){return $false}
  }
  if($Health.tool_count -isnot [int] -and $Health.tool_count -isnot [long]){return $false}
  if($Health.tool_count -ne $actual.Count -or -not $actual.SetEquals($expected)){return $false}
  return (
   $Health.ok -is [bool] -and $Health.ok -eq $true -and
   $Health.service -ceq 'raios-universal-mcp' -and $Health.transport -ceq 'streamable-http' -and
   $Health.second_gateway -is [bool] -and $Health.second_gateway -eq $false -and
   $Health.get_sse -is [bool] -and $Health.get_sse -eq $true -and
   $Health.stateless -is [bool] -and $Health.stateless -eq $false -and
   $Health.channel -ceq 'streamable-http-session' -and
   $Health.hosted_dcr_required -is [bool] -and $Health.hosted_dcr_required -eq $false
  )
 } catch {return $false}
}
