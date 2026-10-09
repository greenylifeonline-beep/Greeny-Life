"""Patch the runtime C5 user lane into Universal-MCP-owned Desktop Commander mode."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

DCR_STATE_DECL = r"$DcrState='C:\Users\Ghanam\.raios\runtime\remote-access\rdc-system-direct\rdc-supervisor-state.json'"
MARKER_DECL = r"$NativeDcrMarker=Join-Path $Root 'DCR-NATIVE-PROVIDER.enabled'"

INJECTION = r"""function Ensure-Dcr {
 try{
  if(Test-Path -LiteralPath $NativeDcrMarker){
   try{
    if(Test-Path -LiteralPath $DcrState){
     $nativeState=Get-Content -LiteralPath $DcrState -Raw|ConvertFrom-Json
     $supPid=[int]$nativeState.supervisor_pid
     if($supPid -gt 4){
      $sup=Get-CimInstance Win32_Process -Filter ('ProcessId='+$supPid) -ErrorAction SilentlyContinue
      if($sup -and [string]$sup.CommandLine -like ('*'+$Dcr+'*') -and [string]$sup.CommandLine -match '--supervise'){
       Stop-Process -Id $supPid -Force -ErrorAction SilentlyContinue
       ('DCR_HOSTED_RETIRED|'+[DateTimeOffset]::UtcNow.ToString('o')+'|PID='+$supPid)|Add-Content -LiteralPath $Out -Encoding UTF8
      }
     }
    }
   }catch{
    try{('DCR_HOSTED_RETIRE_FAIL|'+[DateTimeOffset]::UtcNow.ToString('o')+'|'+$_.Exception.Message)|Add-Content -LiteralPath $Err -Encoding UTF8}catch{}
   }
   $dcrProc=$null
   return
  }
"""


def patch(lane: Path, lane_v2: Path, marker: Path) -> None:
    text = lane.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    if "$NativeDcrMarker=" not in text:
        if DCR_STATE_DECL not in text:
            raise RuntimeError("DCR_STATE_DECLARATION_NOT_FOUND")
        text = text.replace(DCR_STATE_DECL, DCR_STATE_DECL + "\n" + MARKER_DECL, 1)

    if "DCR_HOSTED_RETIRED" not in text:
        header = "function Ensure-Dcr {\n try{"
        if header not in text:
            raise RuntimeError("ENSURE_DCR_FUNCTION_HEADER_NOT_FOUND")
        text = text.replace(header, INJECTION.rstrip("\n"), 1)

    lane.write_text(text.replace("\n", "\r\n"), encoding="utf-8")
    lane_v2.write_text(text.replace("\n", "\r\n"), encoding="utf-8")
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(
        json.dumps(
            {
                "schema": "raios.dcr-native-provider-mode.v1",
                "enabled": True,
                "authority": "RAIOS-C5",
                "gateway": "RAIOS Universal MCP",
                "endpoint": "http://127.0.0.1:8788/mcp",
                "provider": "desktop_commander",
                "transport": "local_stdio",
                "hosted_remote_required": False,
                "activated_at": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lane", required=True)
    ap.add_argument("--lane-v2", required=True)
    ap.add_argument("--marker", required=True)
    args = ap.parse_args()
    patch(Path(args.lane), Path(args.lane_v2), Path(args.marker))
    print("C5_NATIVE_PROVIDER_PATCH=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
