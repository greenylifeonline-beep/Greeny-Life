import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from src.raios.command_center.message_worker import MessageWorker, atomic

class MessageWorkerTests(unittest.TestCase):
    def make_worker(self,max_attempts=3):
        td=tempfile.TemporaryDirectory()
        root=Path(td.name)/"Greeny-Life";root.mkdir()
        (root/".git").mkdir()
        runtime=Path(td.name)/"runtime"
        return td,MessageWorker(root,runtime,poll_seconds=.01,max_attempts=max_attempts)

    def test_enqueue_deliver_and_idempotent_ack(self):
        td,worker=self.make_worker()
        try:
            msg=worker.enqueue("C1",["C2","C6"],"hello","T-1")
            first=worker.scan_once();second=worker.scan_once()
            mid=msg["message_id"]
            self.assertEqual(first["delivered"],1)
            self.assertEqual(first["pending_actor_ack"],1)
            self.assertEqual(second["delivered"],0)
            state=json.loads((worker.state/f"{mid}.json").read_text())
            self.assertEqual(state["status"],"DELIVERED_PENDING_ACTOR_ACK")
            self.assertFalse(state["actor_ack"])
            registry=json.loads((worker.fabric/"WORKER-REGISTRY.json").read_text())
            self.assertEqual(registry["workers"][0]["owner"],"RAIOS_SYSTEM")
            self.assertFalse(registry["workers"][0]["permanent_lock"])
            for seat in ("C2","C6"):
                self.assertTrue((worker.deliveries/seat/f"{mid}.json").exists())
                ack=json.loads((worker.outbox/f"{mid}.{seat}.delivery.ack.json").read_text())
                self.assertEqual(ack["ack_type"],"DELIVERY_ACK")
                self.assertEqual(ack["status"],"QUEUED_FOR_SEAT")
        finally:td.cleanup()
    def test_all_expands_canonical_seats(self):
        td,worker=self.make_worker()
        try:
            targets=[f"C{i}" for i in range(1,13)]
            msg=worker.enqueue("C1",targets,"broadcast")
            worker.scan_once();mid=msg["message_id"]
            self.assertTrue((worker.deliveries/"C6"/f"{mid}.json").exists())
            self.assertTrue((worker.deliveries/"C12"/f"{mid}.json").exists())
            self.assertFalse((worker.deliveries/"RAIOS-WORKER"/f"{mid}.json").exists())
            self.assertFalse((worker.deliveries/"COMMAND_CENTER"/f"{mid}.json").exists())
            self.assertEqual(worker.worker_id.split("@",1)[0],"RAIOS-WORKER")
        finally:td.cleanup()

    def test_concurrent_atomic_writers_leave_valid_json(self):
        td,worker=self.make_worker()
        try:
            path=worker.fabric/"race.json"
            threads=[threading.Thread(target=atomic,args=(path,{"writer":i})) for i in range(20)]
            [t.start() for t in threads];[t.join() for t in threads]
            self.assertIn(json.loads(path.read_text())["writer"],range(20))
            self.assertEqual(list(path.parent.glob("race.json.*.tmp")),[])
        finally:td.cleanup()


    def test_worker_survives_transient_io_failure_and_recovers_health(self):
        td,worker=self.make_worker()
        try:
            original=worker.scan_once;calls={"count":0}
            def flaky_scan():
                calls["count"]+=1
                if calls["count"]==1:raise PermissionError("simulated registry race")
                return original()
            worker.scan_once=flaky_scan
            thread=worker.start()
            deadline=time.time()+2
            while calls["count"]<2 and time.time()<deadline:time.sleep(.01)
            while not worker.status()["healthy"] and time.time()<deadline:time.sleep(.01)
            status=worker.status()
            self.assertTrue(thread.is_alive())
            self.assertGreaterEqual(calls["count"],2)
            self.assertTrue(status["heartbeat_current"])
            self.assertTrue(status["healthy"])
            self.assertIsNone(status["last_error"])
        finally:
            worker.stop()
            if worker.thread:worker.thread.join(timeout=1)
            td.cleanup()


    def test_historical_actor_ack_prevents_obsolete_message_dead_letter(self):
        td,worker=self.make_worker(max_attempts=1)
        try:
            mid="MSG-historical"
            path=worker.inbox/f"{mid}.json"
            path.write_text(json.dumps({"schema":"raios.message.v1","message_id":mid,"target":"C2-OBS","payload":{"text":"old","task_id":"T-HIST"}}),encoding="utf-8")
            receipt=worker.receipts/f"{mid}.C2-OBS.ack.receipt.json"
            receipt.write_text(json.dumps({"schema":"raios.message-ack.v1","message_id":mid,"actor":"C2-OBS","status":"ACKNOWLEDGED","at":"2026-08-27T00:00:00Z"}),encoding="utf-8")
            result=worker.scan_once()
            state=json.loads((worker.state/f"{mid}.json").read_text())
            self.assertEqual(result["dead_letter"],0)
            self.assertEqual(state["status"],"ACTOR_ACK")
            self.assertTrue(state["historical_ack"])
            self.assertFalse((worker.dead/path.name).exists())
        finally:td.cleanup()

    def test_invalid_message_reaches_dead_letter(self):
        td,worker=self.make_worker(max_attempts=1)
        try:
            path=worker.inbox/"MSG-invalid.json"
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text('{"schema":"wrong","message_id":"MSG-invalid"}',encoding="utf-8")
            result=worker.scan_once()
            self.assertEqual(result["dead_letter"],1)
            self.assertTrue((worker.dead/path.name).exists())
        finally:td.cleanup()

    def test_actor_ack_terminal_index_skips_reloading_after_restart(self):
        td,worker=self.make_worker()
        try:
            msg=worker.enqueue("C1",["C2"],"hello")
            worker.scan_once()
            mid=msg["message_id"]
            self.assertFalse(worker.terminal_index.exists())
            receipt=worker.receipts/f"{mid}.C2.actor.ack.receipt.json"
            receipt.write_text(json.dumps({
                "schema":"raios.actor-ack.v1","message_id":mid,
                "actor":"C2","target":"C2","status":"ACKNOWLEDGED",
                "at":"2026-10-10T00:00:00Z"
            }),encoding="utf-8")
            acked=worker.scan_once()
            self.assertEqual(acked["actor_ack"],1)
            self.assertTrue(worker.terminal_index.exists())
            index=json.loads(worker.terminal_index.read_text())
            self.assertEqual(index["terminality_source"],"ACTOR_ACK_OR_COMPLETION")
            restarted=MessageWorker(worker.repo,worker.runtime,poll_seconds=.01,max_attempts=3)
            original=restarted._attempts
            def guarded(message_id):
                if message_id==mid:
                    raise AssertionError("actor-acked state should be skipped by terminal index")
                return original(message_id)
            restarted._attempts=guarded
            result=restarted.scan_once()
            self.assertEqual(result["terminal_cache_hits"],1)
            self.assertEqual(result["delivered"],0)
        finally:td.cleanup()

    def test_progress_heartbeat_is_written_during_scan_not_only_after_completion(self):
        td,worker=self.make_worker()
        try:
            for i in range(4):
                mid=f"MSG-progress-{i}"
                (worker.inbox/f"{mid}.json").write_text(json.dumps({
                    "schema":"raios.message.v1","message_id":mid,"target":"C2",
                    "payload":{"to":["C2"],"text":"probe"}
                }),encoding="utf-8")
            worker.heartbeat_interval_seconds=0
            phases=[]
            original=worker.heartbeat
            def capture(last=None):
                phases.append((last or {}).get("scan_phase"))
                return original(last)
            worker.heartbeat=capture
            worker.scan_once()
            self.assertGreaterEqual(len(phases),6)
            self.assertEqual(phases[0],"SCAN_START")
            self.assertEqual(phases[-1],"SCAN_COMPLETE")
            self.assertIn("INBOX_SCAN",phases)
            hb=json.loads((worker.state/"heartbeat.json").read_text())
            self.assertEqual(hb["last_scan"]["scan_phase"],"SCAN_COMPLETE")
            self.assertEqual(hb["head"],worker._head())
        finally:td.cleanup()

    def test_dead_letter_is_quarantined_and_not_reprocessed(self):
        td,worker=self.make_worker(max_attempts=1)
        try:
            mid="MSG-dead-quarantine"
            path=worker.inbox/f"{mid}.json"
            path.write_text(json.dumps({
                "schema":"wrong","message_id":mid,"target":"C2"
            }),encoding="utf-8")
            first=worker.scan_once()
            self.assertEqual(first["dead_letter"],1)
            state_path=worker.state/f"{mid}.json"
            first_state=json.loads(state_path.read_text())
            self.assertFalse(path.exists())
            self.assertTrue((worker.dead/f"{mid}.json").exists())
            second=worker.scan_once()
            second_state=json.loads(state_path.read_text())
            self.assertEqual(second["dead_letter"],0)
            self.assertEqual(second_state["attempts"],first_state["attempts"])
            self.assertEqual(second_state["status"],"DEAD_LETTER")
        finally:td.cleanup()

    def test_delivery_ack_is_not_actor_ack_or_terminal(self):
        td,worker=self.make_worker()
        try:
            msg=worker.enqueue("C1",["C2"],"needs actor ack")
            result=worker.scan_once()
            mid=msg["message_id"]
            state=json.loads((worker.state/f"{mid}.json").read_text())
            delivery_ack=json.loads((worker.receipts/f"{mid}.C2.delivery.ack.receipt.json").read_text())
            self.assertEqual(result["delivered"],1)
            self.assertEqual(delivery_ack["ack_type"],"DELIVERY_ACK")
            self.assertEqual(state["status"],"DELIVERED_PENDING_ACTOR_ACK")
            self.assertNotIn(mid,worker._delivered_terminal)
            self.assertFalse(worker.terminal_index.exists())
        finally:td.cleanup()

    def test_multitarget_requires_all_actor_acks_before_terminality(self):
        td,worker=self.make_worker()
        try:
            msg=worker.enqueue("C1",["C2","C3"],"all must ack","T-MULTI")
            worker.scan_once();mid=msg["message_id"]
            (worker.receipts/f"{mid}.C2.actor.ack.receipt.json").write_text(json.dumps({
                "schema":"raios.actor-ack.v1","message_id":mid,
                "actor":"C2","target":"C2","status":"ACKNOWLEDGED",
                "at":"2026-10-10T00:00:00Z"
            }),encoding="utf-8")
            partial=worker.scan_once()
            state=json.loads((worker.state/f"{mid}.json").read_text())
            self.assertEqual(partial["actor_ack"],0)
            self.assertEqual(state["status"],"DELIVERED_PENDING_ACTOR_ACK")
            (worker.receipts/f"{mid}.C3.actor.ack.receipt.json").write_text(json.dumps({
                "schema":"raios.actor-ack.v1","message_id":mid,
                "actor":"C3","target":"C3","status":"ACKNOWLEDGED",
                "at":"2026-10-10T00:00:01Z"
            }),encoding="utf-8")
            complete=worker.scan_once()
            state=json.loads((worker.state/f"{mid}.json").read_text())
            self.assertEqual(complete["actor_ack"],1)
            self.assertEqual(state["status"],"ACTOR_ACK")
            self.assertIn(mid,worker._delivered_terminal)
        finally:td.cleanup()

    def test_pending_actor_ack_redelivery_is_bounded(self):
        td,worker=self.make_worker()
        try:
            worker.ack_redelivery_seconds=0
            worker.max_ack_redeliveries=1
            msg=worker.enqueue("C1",["C2"],"bounded redelivery")
            worker.scan_once();mid=msg["message_id"]
            second=worker.scan_once()
            self.assertEqual(second["redelivered"],1)
            third=worker.scan_once()
            state=json.loads((worker.state/f"{mid}.json").read_text())
            self.assertEqual(third["actor_ack_blocked"],1)
            self.assertEqual(state["status"],"BLOCKED_ACTOR_ACK")
            self.assertEqual(state["ack_redelivery_count"],1)
            self.assertNotIn(mid,worker._delivered_terminal)
        finally:td.cleanup()

    def test_legacy_delivery_terminal_index_is_not_trusted(self):
        td,worker=self.make_worker()
        try:
            mid="MSG-legacy-terminal"
            worker.terminal_index.parent.mkdir(parents=True,exist_ok=True)
            worker.terminal_index.write_text(json.dumps({
                "schema":"raios.message-worker-delivered-terminal-index.v1",
                "message_ids":[mid]
            }),encoding="utf-8")
            restarted=MessageWorker(worker.repo,worker.runtime,poll_seconds=.01,max_attempts=3)
            self.assertNotIn(mid,restarted._delivered_terminal)
        finally:td.cleanup()

    def test_delivery_moves_message_out_of_inbox_into_pending_ack_lane(self):
        td,worker=self.make_worker()
        try:
            msg=worker.enqueue("C1",["C2"],"compact inbox")
            mid=msg["message_id"]
            worker.scan_once()
            self.assertFalse((worker.inbox/f"{mid}.json").exists())
            self.assertTrue((worker.pending_ack/f"{mid}.json").exists())
            self.assertTrue(worker.pending_ack_index.exists())
            state=json.loads((worker.state/f"{mid}.json").read_text())
            self.assertEqual(state["status"],"DELIVERED_PENDING_ACTOR_ACK")
        finally:td.cleanup()

    def test_unlinked_terminal_message_keeps_receipt_not_full_content(self):
        td,worker=self.make_worker()
        try:
            msg=worker.enqueue("C1",["C2"],"transient message")
            mid=msg["message_id"];worker.scan_once()
            (worker.receipts/f"{mid}.C2.actor.ack.receipt.json").write_text(json.dumps({
                "schema":"raios.actor-ack.v1","message_id":mid,
                "actor":"C2","target":"C2","status":"ACKNOWLEDGED",
                "at":"2026-10-10T00:00:00Z"
            }),encoding="utf-8")
            worker.scan_once()
            self.assertFalse((worker.pending_ack/f"{mid}.json").exists())
            self.assertFalse((worker.archive/f"{mid}.json").exists())
            self.assertFalse((worker.state/f"{mid}.json").exists())
            self.assertTrue((worker.receipts/f"{mid}.actor-ack.lifecycle.receipt.json").exists())
        finally:td.cleanup()

    def test_task_linked_terminal_message_is_archived(self):
        td,worker=self.make_worker()
        try:
            msg=worker.enqueue("C1",["C2"],"retain task evidence","T-RETAIN")
            mid=msg["message_id"];worker.scan_once()
            (worker.receipts/f"{mid}.C2.actor.ack.receipt.json").write_text(json.dumps({
                "schema":"raios.actor-ack.v1","message_id":mid,
                "actor":"C2","target":"C2","status":"ACKNOWLEDGED",
                "at":"2026-10-10T00:00:00Z"
            }),encoding="utf-8")
            worker.scan_once()
            self.assertFalse((worker.pending_ack/f"{mid}.json").exists())
            self.assertTrue((worker.archive/f"{mid}.json").exists())
            state=json.loads((worker.state/f"{mid}.json").read_text())
            self.assertEqual(state["status"],"ACTOR_ACK")
        finally:td.cleanup()

    def test_small_scan_budget_progresses_by_compacting_processed_inbox(self):
        td,worker=self.make_worker()
        try:
            worker.max_messages_per_scan=4
            mids=[]
            for i in range(6):
                msg=worker.enqueue("C1",["C2"],f"m-{i}")
                mids.append(msg["message_id"])
            for _ in range(4):
                worker.scan_once()
            remaining=list(worker.inbox.glob("MSG-*.json"))
            self.assertEqual(remaining,[])
            self.assertEqual(len(list(worker.pending_ack.glob("MSG-*.json"))),6)
        finally:td.cleanup()

    def test_long_workflow_keeps_heartbeat_alive_while_run_cycle_is_blocked(self):
        td,worker=self.make_worker()
        try:
            class SlowWorkflow:
                def run_cycle(self,_worker):
                    time.sleep(.08)
                    return {"slow_workflow_completed":1}
            worker.configure_workflow(SlowWorkflow())
            worker.heartbeat_interval_seconds=.01
            phases=[]
            original=worker.heartbeat
            def capture(last=None):
                phases.append((last or {}).get("scan_phase"))
                return original(last)
            worker.heartbeat=capture
            result=worker.scan_once()
            self.assertEqual(result["slow_workflow_completed"],1)
            self.assertGreaterEqual(phases.count("WORKFLOW_RUNNING"),2)
            self.assertIn("WORKFLOW_START",phases)
            self.assertEqual(phases[-1],"SCAN_COMPLETE")
            hb=json.loads((worker.state/"heartbeat.json").read_text())
            self.assertEqual(hb["last_scan"]["scan_phase"],"SCAN_COMPLETE")
            self.assertTrue(worker.status()["heartbeat_current"])
        finally:td.cleanup()

if __name__=="__main__":unittest.main()
