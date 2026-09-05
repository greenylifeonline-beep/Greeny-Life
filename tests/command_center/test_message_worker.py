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
            self.assertEqual(second["delivered"],0)
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
            path.write_text(json.dumps({"schema":"raios.message.v1","message_id":mid,"target":"C2-OBS","payload":{"text":"old"}}),encoding="utf-8")
            receipt=worker.receipts/f"{mid}.C2-OBS.ack.receipt.json"
            receipt.write_text(json.dumps({"schema":"raios.message-ack.v1","message_id":mid,"actor":"C2-OBS","status":"ACKNOWLEDGED","at":"2026-08-27T00:00:00Z"}),encoding="utf-8")
            result=worker.scan_once()
            state=json.loads((worker.state/f"{mid}.json").read_text())
            self.assertEqual(result["dead_letter"],0)
            self.assertEqual(state["status"],"DELIVERED")
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

    def test_delivered_terminal_index_skips_reloading_old_state_after_restart(self):
        td,worker=self.make_worker()
        try:
            msg=worker.enqueue("C1",["C2"],"hello")
            worker.scan_once()
            mid=msg["message_id"]
            self.assertTrue(worker.terminal_index.exists())
            restarted=MessageWorker(worker.repo,worker.runtime,poll_seconds=.01,max_attempts=3)
            original=restarted._attempts
            def guarded(message_id):
                if message_id==mid:
                    raise AssertionError("delivered state should be skipped by terminal index")
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
            self.assertIn("SCANNING",phases)
            hb=json.loads((worker.state/"heartbeat.json").read_text())
            self.assertEqual(hb["last_scan"]["scan_phase"],"SCAN_COMPLETE")
            self.assertEqual(hb["head"],worker._head())
        finally:td.cleanup()

    def test_dead_letter_is_not_reprocessed_but_can_recover_from_real_actor_ack(self):
        td,worker=self.make_worker(max_attempts=1)
        try:
            mid="MSG-dead-recover"
            path=worker.inbox/f"{mid}.json"
            path.write_text(json.dumps({
                "schema":"wrong","message_id":mid,"target":"C2"
            }),encoding="utf-8")
            first=worker.scan_once()
            self.assertEqual(first["dead_letter"],1)
            state_path=worker.state/f"{mid}.json"
            first_state=json.loads(state_path.read_text())
            second=worker.scan_once()
            second_state=json.loads(state_path.read_text())
            self.assertEqual(second["dead_letter"],0)
            self.assertEqual(second_state["attempts"],first_state["attempts"])
            receipt=worker.receipts/f"{mid}.C2.actor.ack.receipt.json"
            receipt.write_text(json.dumps({
                "schema":"raios.actor-ack.v1","message_id":mid,
                "actor":"C2","status":"ACKNOWLEDGED","at":"2026-09-05T00:00:00Z"
            }),encoding="utf-8")
            third=worker.scan_once()
            recovered=json.loads(state_path.read_text())
            self.assertEqual(third["historical_ack_recovered"],1)
            self.assertEqual(recovered["status"],"DELIVERED")
        finally:td.cleanup()

if __name__=="__main__":unittest.main()
