from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid

from datetime import datetime,timezone
from pathlib import Path

from fastapi import (
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect
)

from pydantic import AliasChoices,BaseModel,Field,field_validator


HERE=Path(__file__).resolve().parent

sys.path.insert(
    0,
    str(HERE)
)

from .ollama_client import (
    CortexResult,
    OllamaCortexClient
)
from .model_fabric import C5ModelFabric

from .learning_trace import (
    TrainingStore,
    TrainingTurn
)
from .cognitive_loop import (
    assimilate_turn,
    format_grounded_user_message,
    loop_status,
    retrieve_grounding,
)


def utc():
    return datetime.now(timezone.utc).isoformat()


def deployment_environment():
    manifest = Path(os.getenv("RAIOS_RUNTIME_ROOT", str(Path.home() / ".raios" / "runtime" / "c5"))) / "deployment.json"
    try:
        data = json.loads(manifest.read_text(encoding="utf-8-sig"))
    except Exception:
        data = {}
    return {
        "dependency_audit": data.get("dependency_audit", "UNPROVEN"),
        "pytest_available": bool(data.get("pytest_available")),
        "requirements_sha256": data.get("requirements_sha256"),
        "packages": data.get("packages") or ["c5_gateway"],
    }


RUNTIME_ROOT=Path(
    os.getenv(
        "RAIOS_RUNTIME_ROOT",
        str(Path.home()/".raios"/"runtime"/"c5")
    )
)

TRAINING_ROOT=Path(
    os.getenv(
        "RAIOS_C5_TRAINING_ROOT",
        str(RUNTIME_ROOT/"learning"/"supervised-training")
    )
)

client=OllamaCortexClient()
model_fabric=C5ModelFabric()

training=None

app=FastAPI(
    title="RAIOS Conversational Cortex",
    version="3.0"
)


class ChatRequest(BaseModel):

    text:str=Field(
        validation_alias=AliasChoices("text","message"),
        min_length=1,
        max_length=200_000
    )

    language:str=Field(
        default="auto",
        validation_alias=AliasChoices("language","locale")
    )

    conversation_id:str|None=None

    task_id:str|None=None

    teacher:str="HUMAN"

    training_mode:bool=False

    stream:bool=False

    timeout_seconds:float=Field(
        default=120.0,
        ge=1.0,
        le=600.0
    )

    @field_validator("text")
    @classmethod
    def reject_blank_text(cls,value:str):
        normalized=value.strip()
        if not normalized:
            raise ValueError("EMPTY_TEXT")
        return normalized


SYSTEM_PROMPT="""
You are C5@AG, the RAIOS student language worker behind HTTP 127.0.0.1:8766.

You are NOT Main Cortex. Main Cortex identity is qwen3.6:35b-a3b, owned by C1, state HOLD.

The user message contains a GROUNDING_ENVELOPE. That envelope is truth for this turn.
Conversation history and your own prior answers are not execution truth.
If grounding count is 0, say EVIDENCE=NONE_AVAILABLE for execution claims.

This HTTP turn does not run tools, GL tasks, clusters, or file mutations.

Never say executed, started, initialized, running, completed, confirmed, deployed,
connected, repaired, wrote, or changed unless the envelope contains a bound receipt.

If C1 says hi/hello: greet briefly and identify as C5@AG student. Do not mention GL tasks.
If the input is nonsense: ask a short clarification.
If asked whether you executed GL work: answer NOT_PROVEN.
If no receipt exists: EVIDENCE=NONE_AVAILABLE.
"""


def _raios_inference(messages, task_id=None):
    """Use the single RAIOS Model Fabric first; legacy Ollama is bounded fallback."""
    routed=model_fabric.chat(
        messages, task_class="NORMAL_CHAT", privacy_class="local_preferred",
        task_id=task_id, max_tokens=client.num_predict,
    )
    gateway=routed.get("gateway") or {}
    dispatch=gateway.get("dispatch") or {}
    if dispatch.get("ok") and dispatch.get("content"):
        return CortexResult(
            request_id=str(uuid.uuid4()), ok=True,
            status_code=dispatch.get("http_status"),
            model=str(dispatch.get("model_id") or "RAIOS_MODEL_FABRIC"),
            content=str(dispatch.get("content") or ""), error=None,
            latency_seconds=float(dispatch.get("latency_ms") or 0)/1000.0,
            raw={"system_identity":"RAIOS/C5","model_fabric":True,"route":gateway},
            created_at=utc(),
        )
    return client.chat(messages, stream=False, timeout=120.0)


def execute_chat(
    text,
    language,
    conversation_id,
    task_id,
    teacher,
    training_mode,
    timeout_seconds=120.0
):

    cid=(
        conversation_id
        or
        str(uuid.uuid4())
    )

    grounding=retrieve_grounding(text)
    grounded_text=format_grounded_user_message(text,grounding)
    language_key=str(language or "auto").lower()
    language_instruction=(
        "Respond only in clear Arabic. Preserve Arabic Unicode; do not transliterate."
        if language_key.startswith("ar")
        else "Respond in the user requested language."
    )

    result=_raios_inference(
        [
            {
                "role":"system",
                "content":SYSTEM_PROMPT + "\n" + language_instruction
            },
            {
                "role":"user",
                "content":grounded_text
            }
        ],
        task_id=task_id,
    )

    store=TrainingStore(TRAINING_ROOT)
    store.append(
        TrainingTurn(
            task_id=task_id,
            conversation_id=cid,
            teacher=teacher,
            student="RAIOS_STUDENT",
            phase="ATTEMPT",
            attempt=1,
            prompt=text,
            student_response=result.content,
            execution_required=False,
            scores={"grounding_count":float(grounding.get("count") or 0)},
            mastery=False,
            state=(
                "OBSERVED"
                if result.ok
                else
                "FAILED_ATTEMPT"
            )
        )
    )

    assimilated=None
    if result.ok:
        try:
            assimilated=assimilate_turn(
                prompt=text,
                response=result.content,
                conversation_id=cid,
                model=result.model,
                grounding=grounding,
            )
        except Exception as assimilate_error:
            assimilated={"status":"FAILED","error":f"{type(assimilate_error).__name__}:{assimilate_error}"}

    if not result.ok:

        timeout_failure=(
            result.status_code is None
            and
            result.error
            and
            (
                result.error.startswith("TimeoutError::")
                or
                result.error.startswith("socket.timeout::")
            )
        )

        raise HTTPException(
            status_code=504 if timeout_failure else 502,
            detail={
                "error":"STUDENT_TIMEOUT" if timeout_failure else "STUDENT_FAILURE",
                "legacy_error":"MAIN_CORTEX_TIMEOUT" if timeout_failure else "MAIN_CORTEX_FAILURE",
                "model":result.model,
                "cortex_request_id":
                    result.request_id,
                "upstream_status":
                    result.status_code,
                "reason":
                    result.error,
                "latency_seconds":
                    result.latency_seconds
            }
        )

    return {
        "status":"OK",
        "system_identity":"RAIOS/C5",
        "model_fabric":True,
        "conversation_id":cid,
        "cortex_request_id":
            result.request_id,
        "model":result.model,
        "role":"STUDENT",
        "main_cortex_identity":"qwen3.6:35b-a3b",
        "main_cortex_state":"HOLD",
        "language":language,
        "response":result.content,
        "content":result.content,
        "reply":result.content,
        "grounding":{
            "count":grounding.get("count"),
            "latency_ms":grounding.get("latency_ms"),
            "receipts":grounding.get("receipts") or [],
            "evidence_refs":grounding.get("evidence_refs") or [],
            "verification":(grounding.get("search") or {}).get("verification"),
            "contradictions":(grounding.get("search") or {}).get("contradictions") or [],
            "shared_search_cortex":grounding.get("shared_search_cortex") is True,
        },
        "assimilated":assimilated,
        "closed_loop":True,
        "latency_seconds":
            result.latency_seconds,
        "runtime_source":"CANONICAL_DEPLOYMENT",
        "canonical_head":os.getenv("RAIOS_CANONICAL_HEAD","UNKNOWN"),
        "timestamp":utc()
    }


@app.get("/health")
def health():
    """Bounded runtime readiness. Inference benchmarking is intentionally separate."""
    try:
        registry=model_fabric.router.registry()
        live_engines=[
            row for row in (registry.get("providers") or [])
            if row.get("availability") == "LIVE" and row.get("enabled") is not False
        ]
        fabric_ready=bool(live_engines)
        fabric_error=None
    except Exception as e:
        registry={}
        live_engines=[]
        fabric_ready=False
        fabric_error=f"{type(e).__name__}:{e}"

    return {
        "status":"ONLINE" if fabric_ready else "DEGRADED",
        "system_identity":"RAIOS/C5",
        "gateway":True,
        "model_fabric":True,
        "model_fabric_ready":fabric_ready,
        "live_engine_count":len(live_engines),
        "live_engines":[str(x.get("model_id") or x.get("provider_id") or "") for x in live_engines],
        "model_fabric_error":fabric_error,
        "inference_probe":"SEPARATE_BOUNDED_PROBE",
        "cognitive_loop":loop_status(include_summaries=False),
        "environment":deployment_environment(),
        "runtime_source":"CANONICAL_DEPLOYMENT",
        "canonical_head":os.getenv("RAIOS_CANONICAL_HEAD","UNKNOWN"),
        "training_root":str(TRAINING_ROOT),
        "timestamp":utc()
    }


@app.get("/v1/cognitive/status")
def cognitive_status():
    return loop_status()


@app.post("/v1/chat")
@app.post("/api/chat")
def chat(req:ChatRequest):

    return execute_chat(
        req.text,
        req.language,
        req.conversation_id,
        req.task_id,
        req.teacher,
        req.training_mode,
        req.timeout_seconds
    )


@app.websocket("/v1/ws/chat")
async def ws_chat(ws:WebSocket):

    await ws.accept()

    try:

        while True:

            msg=await ws.receive_json()

            text=str(
                msg.get("text","")
            ).strip()

            if not text:

                await ws.send_json({
                    "type":"ERROR",
                    "error":"EMPTY_TEXT"
                })

                continue

            await ws.send_json({
                "type":"TURN_STARTED",
                "timestamp":utc()
            })

            try:

                result=await asyncio.to_thread(
                    execute_chat,
                    text,
                    msg.get(
                        "language",
                        "auto"
                    ),
                    msg.get(
                        "conversation_id"
                    ),
                    msg.get(
                        "task_id"
                    ),
                    msg.get(
                        "teacher",
                        "HUMAN"
                    ),
                    msg.get(
                        "training_mode",
                        False
                    ),
                    min(
                        max(
                            float(msg.get("timeout_seconds",120.0)),
                            1.0
                        ),
                        600.0
                    )
                )

                await ws.send_json({
                    "type":"FINAL_RESPONSE",
                    **result
                })

            except Exception as e:

                await ws.send_json({
                    "type":"TURN_FAILED",
                    "error":
                        f"{type(e).__name__}:{e}",
                    "timestamp":utc()
                })

    except WebSocketDisconnect:

        return
