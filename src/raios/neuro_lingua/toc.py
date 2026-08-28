"""Theory of Constraints on live canonical logistics. Not a simulated Goldratt play.

IDENTIFY from recorded WIP. No invented minutes, utilization, or payback.
EXPLOIT = mill existing keepers. SUBORDINATE = do not flood unproven routes.
ELEVATE requires C1. REPEAT: constraint may move. Does not close GL-005.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
SHIPMENTS = ROOT / "canonical" / "logistics" / "shipments.json"
CLEARANCE = ROOT / "canonical" / "logistics" / "customs-clearance.json"
STOCK = ROOT / "canonical" / "inventory" / "stock-levels.json"
WAREHOUSES = ROOT / "canonical" / "inventory" / "warehouses.json"

LAWS = (
    "TOC_IDENTIFY_FROM_LIVE_WIP",
    "INVENTED_MINUTES_NE_CONSTRAINT",
    "PRINTED_IMPROVEMENT_NE_THROUGHPUT",
    "ELEVATE_REQUIRES_C1",
    "GULF_WAREHOUSE_ABSENT_IN_CANONICAL",
    "EUROPE_ORIGIN_ABSENT_IN_CANONICAL",
    "STATUS_DESYNC_IS_A_CONSTRAINT",
    "GL003_NEXT_ROUTE_NE_FILLED_HERE",
    "LIVE_PATH_BEFORE_NEW_LAYER",
    "REUSE_BEFORE_BUILD",
)

PASTE_CLAIMS = (
    {
        "claim": "الشحن من أوروبا AvgTime=45 Capacity=100 Load=85",
        "verdict": "FALSIFIED_EUROPE_ORIGIN_ABSENT",
    },
    {
        "claim": "التخليص الجمركي مصر AvgTime=120 Capacity=80 Load=95",
        "verdict": "FALSIFIED_NO_DURATION_OR_CAPACITY_FIELD",
    },
    {
        "claim": "المخازن الخليج AvgTime=30 Capacity=120 Load=70",
        "verdict": "FALSIFIED_NO_GULF_WAREHOUSE",
    },
    {
        "claim": "تحسن 15% وحمولة 80 بدل 95",
        "verdict": "FALSIFIED_INVENTED_IMPROVEMENT",
    },
    {
        "claim": "استثمار 5000 دولار واسترداد 45 يوم",
        "verdict": "FALSIFIED_ELEVATE_WITHOUT_C1",
    },
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    return dict(Counter(str(row.get(key) or "UNKNOWN") for row in rows))


def hunt(root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    shipments_doc = _load(base / "canonical" / "logistics" / "shipments.json")
    clearance_doc = _load(base / "canonical" / "logistics" / "customs-clearance.json")
    stock_doc = _load(base / "canonical" / "inventory" / "stock-levels.json")
    warehouse_doc = _load(base / "canonical" / "inventory" / "warehouses.json")
    shipments = list(shipments_doc.get("shipments") or [])
    clearances = list(clearance_doc.get("clearances") or [])
    stock = list(stock_doc.get("stock") or [])
    warehouses = list(warehouse_doc.get("warehouses") or [])
    by_ship = {str(row.get("shipment_id")): row for row in shipments}

    origins = _counts(shipments, "origin")
    ship_status = _counts(shipments, "status")
    markets = _counts(shipments, "market")
    clearance_status = _counts(clearances, "status")
    uncleared = [row for row in clearances if row.get("status") != "cleared"]
    desync: list[dict[str, str]] = []
    for row in clearances:
        ship = by_ship.get(str(row.get("shipment_id"))) or {}
        ship_st = str(ship.get("status") or "MISSING_SHIPMENT")
        cle_st = str(row.get("status") or "UNKNOWN")
        customs_ship = ship_st == "CUSTOMS_CLEARANCE"
        cleared = cle_st == "cleared"
        if customs_ship and cleared:
            desync.append(
                {
                    "shipment_id": str(row.get("shipment_id")),
                    "shipment_status": ship_st,
                    "clearance_status": cle_st,
                    "kind": "SHIP_SAYS_CUSTOMS_LEDGER_CLEARED",
                }
            )
        if (not customs_ship) and (not cleared) and ship_st == "DELIVERED":
            desync.append(
                {
                    "shipment_id": str(row.get("shipment_id")),
                    "shipment_status": ship_st,
                    "clearance_status": cle_st,
                    "kind": "DELIVERED_BUT_UNCLEARED",
                }
            )
        if customs_ship and not cleared:
            desync.append(
                {
                    "shipment_id": str(row.get("shipment_id")),
                    "shipment_status": ship_st,
                    "clearance_status": cle_st,
                    "kind": "ALIGNED_UNCLEARED_CUSTOMS",
                }
            )

    aligned_uncleared_customs = sum(1 for row in desync if row["kind"] == "ALIGNED_UNCLEARED_CUSTOMS")
    ledger_cleared_ship_customs = sum(1 for row in desync if row["kind"] == "SHIP_SAYS_CUSTOMS_LEDGER_CLEARED")
    delivered_uncleared = sum(1 for row in desync if row["kind"] == "DELIVERED_BUT_UNCLEARED")

    gulf_wh = [row for row in warehouses if "gulf" in str(row.get("location") or "").lower() or "uae" in str(row.get("location") or "").lower()]
    europe_origin = sum(1 for row in shipments if "europe" in str(row.get("origin") or "").lower() or "norway" in str(row.get("origin") or "").lower())
    duration_fields = [
        key
        for row in shipments[:1]
        for key in row
        if any(tok in key.lower() for tok in ("duration", "wait", "avg_time", "capacity", "load"))
    ]

    stock_by_wh: dict[str, int] = {}
    for row in stock:
        wid = str(row.get("warehouse_id") or "UNKNOWN")
        stock_by_wh[wid] = stock_by_wh.get(wid, 0) + int(row.get("quantity") or 0)
    warehouse_load = []
    for row in warehouses:
        wid = str(row.get("id"))
        cap = int(row.get("capacity") or 0)
        qty = int(stock_by_wh.get(wid, 0))
        warehouse_load.append(
            {
                "id": wid,
                "name": row.get("name"),
                "location": row.get("location"),
                "capacity": cap,
                "on_hand": qty,
                "over_capacity": bool(cap and qty > cap),
            }
        )

    wip = {
        "packed": int(ship_status.get("PACKED") or 0),
        "at_port": int(ship_status.get("AT_PORT") or 0),
        "customs_shipment_status": int(ship_status.get("CUSTOMS_CLEARANCE") or 0),
        "in_transit": int(ship_status.get("IN_TRANSIT") or 0),
        "shipped": int(ship_status.get("SHIPPED") or 0),
        "delivered": int(ship_status.get("DELIVERED") or 0),
        "clearance_pending": int(clearance_status.get("pending") or 0),
        "clearance_submitted": int(clearance_status.get("submitted") or 0),
        "clearance_cleared": int(clearance_status.get("cleared") or 0),
        "clearance_uncleared": len(uncleared),
        "status_desync": ledger_cleared_ship_customs + delivered_uncleared,
        "aligned_uncleared_customs": aligned_uncleared_customs,
    }

    ranked = sorted(
        (
            ("clearance_uncleared", wip["clearance_uncleared"]),
            ("in_transit", wip["in_transit"]),
            ("at_port", wip["at_port"]),
            ("customs_shipment_status", wip["customs_shipment_status"]),
            ("packed", wip["packed"]),
        ),
        key=lambda item: item[1],
        reverse=True,
    )
    physical = ranked[0][0] if ranked and ranked[0][1] else "NONE"
    over_cap = [row for row in warehouse_load if row["over_capacity"]]
    identify = "status_desync" if wip["status_desync"] else physical
    if over_cap and identify != "status_desync":
        # Over-capacity is recorded, but desync/WIP still decide throughput first.
        pass

    steps = {
        "identify": {
            "constraint": identify,
            "physical_wip_leader": physical,
            "status_desync": wip["status_desync"],
            "warehouse_over_capacity": [row["id"] for row in over_cap],
            "why": (
                "shipment.status and customs-clearance.status disagree; "
                "no duration fields exist to rank by minutes"
                if identify == "status_desync"
                else f"largest recorded unfinished pile is {physical}={wip.get(physical)}"
            ),
        },
        "exploit": {
            "do": [
                "python3 scripts/ai-os/raios_c5_grind.py",
                "read TRADE-GOVERNANCE.md TRADE-TRACEABILITY.md",
                "do not invent 15% improvement",
            ],
            "not": [
                "SAP/Oracle API",
                "new bottleneck simulator",
                "fill GL-003 UAE/Norway Next routes",
            ],
            "documents_already_present": all(
                set(row.get("documents") or []) >= {"invoice", "packing_list", "certificate_of_origin"}
                for row in clearances
            ),
        },
        "subordinate": {
            "do": [
                "do not pack more origin WIP into uncleared customs",
                "do not fill greens-nature-uae-brain or norway Next route",
            ],
            "uae_next_route": False,
            "norway_next_route": False,
        },
        "elevate": {
            "allowed": False,
            "reason": "ELEVATE_REQUIRES_C1",
            "rejected_paste_investment_usd": 5000,
        },
        "repeat": {
            "constraint_may_move": True,
            "gl005_proven": False,
        },
    }

    return {
        "schema": "raios.toc.v1",
        "ok": True,
        "canonical": True,
        "simulated": False,
        "origins": origins,
        "europe_origin_count": europe_origin,
        "gulf_warehouse_count": len(gulf_wh),
        "duration_fields": duration_fields,
        "shipments": len(shipments),
        "clearances": len(clearances),
        "markets": markets,
        "ship_status": ship_status,
        "clearance_status": clearance_status,
        "wip": wip,
        "warehouse_load": warehouse_load,
        "desync_sample": [row for row in desync if row["kind"] != "ALIGNED_UNCLEARED_CUSTOMS"][:12],
        "paste_claims": PASTE_CLAIMS,
        "steps": steps,
        "law": list(LAWS),
        "wal_written": False,
        "gl005_proven": False,
    }
