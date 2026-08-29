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

from pydantic import BaseModel


HERE=Path(__file__).resolve().parent

sys.path.insert(
    0,
    str(HERE)
)

from .ollama_client import (
    OllamaCortexClient
)

from .learning_trace import (
    TrainingStore,
    TrainingTurn
)


def utc():
    return datetime.now(timezone.utc).isoformat()


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

training=None

app=FastAPI(
    title="RAIOS Conversational Cortex",
    version="3.0"
)


class ChatRequest(BaseModel):

    text:str

    language:str="auto"

    conversation_id:str|None=None

    task_id:str|None=None

    teacher:str="HUMAN"

    training_mode:bool=False


SYSTEM_PROMPT="""
You are C5@AG, a local RAIOS language worker behind HTTP 127.0.0.1:8766.

The user message may contain a GROUNDING_ENVELOPE. That envelope is truth for this turn.
Conversation history and your own prior answers are not execution truth.

This HTTP turn does not run tools, GL tasks, clusters, or file mutations.

Never say executed, started, initialized, running, completed, confirmed, deployed,
connected, repaired, wrote, or changed unless the envelope contains a bound receipt.

If C1 says hi/hello: greet briefly and identify as C5@AG. Do not mention GL tasks.
If the input is nonsense: ask a short clarification.
If asked whether you executed GL work: answer NOT_PROVEN.
If no receipt exists: EVIDENCE=NONE_AVAILABLE.
"""


def execute_chat(
    text,
    language,
    conversation_id,
    task_id,
    teacher,
    training_mode
):

    cid=(
        conversation_id
        or
        str(uuid.uuid4())
    )

    result=client.chat(
        [
            {
                "role":"system",
                "content":SYSTEM_PROMPT
            },
            {
                "role":"user",
                "content":text
            }
        ]
    )

    if training_mode:

        store=TrainingStore(TRAINING_ROOT)

        store.append(
            TrainingTurn(
                task_id=task_id,
                conversation_id=cid,
                teacher=teacher,
                student="RAIOS_MAIN_CORTEX",
                phase="ATTEMPT",
                attempt=1,
                prompt=text,
                student_response=result.content,
                execution_required=False,
                scores={},
                mastery=False,
                state=(
                    "OBSERVED"
                    if result.ok
                    else
                    "FAILED_ATTEMPT"
                )
            )
        )

    if not result.ok:

        raise HTTPException(
            status_code=502,
            detail={
                "error":"MAIN_CORTEX_FAILURE",
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
        "conversation_id":cid,
        "cortex_request_id":
            result.request_id,
        "model":result.model,
        "language":language,
        "response":result.content,
        "latency_seconds":
            result.latency_seconds,
        "runtime_source":"CANONICAL_DEPLOYMENT",
        "canonical_head":os.getenv("RAIOS_CANONICAL_HEAD","UNKNOWN"),
        "timestamp":utc()
    }


@app.get("/health")
def health():

    try:

        model_health=client.health()

    except Exception as e:

        return {
            "status":"DEGRADED",
            "gateway":True,
            "main_cortex":False,
            "error":
                f"{type(e).__name__}:{e}",
            "runtime_source":"CANONICAL_DEPLOYMENT",
            "canonical_head":os.getenv("RAIOS_CANONICAL_HEAD","UNKNOWN"),
            "timestamp":utc()
        }

    return {
        "status":
            "ONLINE"
            if model_health.get(
                "required_model_present"
            )
            else
            "DEGRADED",

        "gateway":True,

        "main_cortex":
            model_health.get(
                "required_model_present",
                False
            ),

        "model":
            client.model,

        "runtime_source":"CANONICAL_DEPLOYMENT",
        "canonical_head":os.getenv("RAIOS_CANONICAL_HEAD","UNKNOWN"),
        "training_root":str(TRAINING_ROOT),
        "timestamp":utc()
    }


@app.post("/v1/chat")
@app.post("/api/chat")
def chat(req:ChatRequest):

    return execute_chat(
        req.text,
        req.language,
        req.conversation_id,
        req.task_id,
        req.teacher,
        req.training_mode
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
