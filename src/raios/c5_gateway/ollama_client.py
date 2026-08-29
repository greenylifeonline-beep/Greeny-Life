from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
import uuid

from dataclasses import dataclass,asdict
from datetime import datetime,timezone
from typing import Any


def utc():
    return datetime.now(timezone.utc).isoformat()


@dataclass
class CortexResult:

    request_id:str

    ok:bool

    status_code:int|None

    model:str

    content:str

    error:str|None

    latency_seconds:float

    raw:dict[str,Any]|None

    created_at:str


class OllamaCortexClient:

    def __init__(
        self,
        model:str|None=None,
        base_url:str|None=None
    ):

        self.model=(
            model
            or
            os.getenv(
                "RAIOS_MAIN_CORTEX",
                "qwen3:0.6b"
            )
        )

        self.base_url=(
            base_url
            or
            os.getenv(
                "RAIOS_OLLAMA_URL",
                "http://127.0.0.1:11434"
            )
        ).rstrip("/")

    def health(self):

        req=urllib.request.Request(
            self.base_url+"/api/tags",
            method="GET"
        )

        with urllib.request.urlopen(
            req,
            timeout=10
        ) as r:

            body=json.loads(
                r.read().decode(
                    "utf-8",
                    errors="replace"
                )
            )

        models=[
            m.get("name")
            for m in body.get(
                "models",
                []
            )
        ]

        return {
            "available":True,
            "models":models,
            "required_model_present":
                self.model in models
        }

    def chat(
        self,
        messages,
        *,
        stream=False,
        timeout=600,
        temperature=0.2,
        num_ctx=16384
    ):

        rid=str(uuid.uuid4())

        started=time.perf_counter()

        payload={
            "model":self.model,
            "messages":messages,
            "stream":stream,
            "options":{
                "temperature":temperature,
                "num_ctx":num_ctx
            }
        }

        req=urllib.request.Request(
            self.base_url+"/api/chat",
            data=json.dumps(
                payload,
                ensure_ascii=False
            ).encode("utf-8"),
            headers={
                "Content-Type":
                    "application/json"
            },
            method="POST"
        )

        try:

            with urllib.request.urlopen(
                req,
                timeout=timeout
            ) as r:

                raw_bytes=r.read()

                text=raw_bytes.decode(
                    "utf-8",
                    errors="replace"
                )

                raw=json.loads(text)

                content=(
                    raw
                    .get("message",{})
                    .get("content","")
                )

                ok=bool(
                    content
                    and
                    str(content).strip()
                )

                return CortexResult(
                    request_id=rid,
                    ok=ok,
                    status_code=r.status,
                    model=self.model,
                    content=str(content),
                    error=None if ok else "EMPTY_MODEL_RESPONSE",
                    latency_seconds=round(
                        time.perf_counter()-started,
                        4
                    ),
                    raw=raw,
                    created_at=utc()
                )

        except urllib.error.HTTPError as e:

            try:
                body=e.read().decode(
                    "utf-8",
                    errors="replace"
                )
            except Exception:
                body=""

            return CortexResult(
                request_id=rid,
                ok=False,
                status_code=e.code,
                model=self.model,
                content="",
                error=f"HTTP_ERROR::{e.code}::{body}",
                latency_seconds=round(
                    time.perf_counter()-started,
                    4
                ),
                raw=None,
                created_at=utc()
            )

        except Exception as e:

            return CortexResult(
                request_id=rid,
                ok=False,
                status_code=None,
                model=self.model,
                content="",
                error=f"{type(e).__name__}::{e}",
                latency_seconds=round(
                    time.perf_counter()-started,
                    4
                ),
                raw=None,
                created_at=utc()
            )


if __name__=="__main__":

    c=OllamaCortexClient()

    print(
        json.dumps(
            c.health(),
            indent=2,
            ensure_ascii=False
        )
    )
