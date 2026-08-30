import json
import tempfile
import unittest
from pathlib import Path
from src.raios.command_center.message_worker import MessageWorker

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

if __name__=="__main__":unittest.main()
