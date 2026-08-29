from __future__ import annotations

import json
import uuid

from dataclasses import dataclass,asdict,field
from datetime import datetime,timezone
from pathlib import Path
from typing import Any


def utc():
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TrainingTurn:

    training_turn_id:str=field(
        default_factory=lambda:str(uuid.uuid4())
    )

    task_id:str|None=None

    conversation_id:str|None=None

    teacher:str="CURSOR"

    student:str="RAIOS"

    phase:str="ATTEMPT"

    attempt:int=1

    prompt:str=""

    student_response:str=""

    execution_required:bool=False

    execution_evidence:list[Any]=field(
        default_factory=list
    )

    teacher_feedback:str=""

    scores:dict[str,float]=field(
        default_factory=dict
    )

    transfer_case:str|None=None

    transfer_result:str|None=None

    mastery:bool=False

    state:str="DISCOVERED"

    created_at:str=field(
        default_factory=utc
    )


class TrainingStore:

    def __init__(self,root):

        self.root=Path(root)

        self.root.mkdir(
            parents=True,
            exist_ok=True
        )

    def append(self,turn:TrainingTurn):

        path=self.root/"training-events.jsonl"

        with path.open(
            "a",
            encoding="utf-8"
        ) as f:

            f.write(
                json.dumps(
                    asdict(turn),
                    ensure_ascii=False
                )
                +"\n"
            )

        return str(path)


if __name__=="__main__":

    import argparse

    p=argparse.ArgumentParser()

    p.add_argument(
        "--root",
        required=True
    )

    args=p.parse_args()

    store=TrainingStore(
        args.root
    )

    test=TrainingTurn(
        prompt="SELFTEST",
        student_response="SELFTEST",
        scores={
            "diagnosis_accuracy":1.0
        }
    )

    print(
        store.append(test)
    )
