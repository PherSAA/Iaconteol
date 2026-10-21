"""Benchmark 1,000/10,000 tareas: métricas medidas, sin promesa de velocidad."""
import argparse, json, tempfile, time
from pathlib import Path
from engine import Network, submit

def benchmark(total=1000,kind="sum_squares",fail_worker=False,timeout=180):
    with tempfile.TemporaryDirectory() as folder:
        net=Network(str(Path(folder)/"bench.sqlite3"),count=8)
        try:
            t0=time.monotonic()
            for i in range(total):
                submit(kind,{"n":200 if kind=="sum_squares" else 1000},net.path)
            queued_s=time.monotonic()-t0
            if fail_worker:net.kill(1)
            limit=time.monotonic()+timeout
            while time.monotonic()<limit:
                s=net.state()
                if s["stats"]["done"]+s["stats"]["failed"]>=total:break
                time.sleep(.12)
            s=net.report();secs=time.monotonic()-t0
            return {"requested":total,"kind":kind,"injected_worker_failure":fail_worker,
                    "elapsed_seconds":round(secs,3),"enqueue_seconds":round(queued_s,3),
                    "end_to_end_throughput":round(s["stats"]["done"]/max(secs,.00001),2),
                    "finished":s["stats"]["done"],"failed":s["stats"]["failed"],
                    "pending":s["stats"]["pending"],"in_process":s["stats"]["running"],
                    "restarts":s["restarts"],"retries":s["attempts_retried"],
                    "duplicate_result_records":s["duplicate_completion_records"],
                    "average_task_latency_seconds":s["average_task_latency_seconds"]}
        finally:net.close()

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--tasks",type=int,choices=[100,1000,10000],default=1000)
    p.add_argument("--kind",choices=["sum_squares","sha256_chain"],default="sum_squares")
    p.add_argument("--fail-worker",action="store_true")
    args=p.parse_args()
    result=benchmark(args.tasks,args.kind,args.fail_worker)
    print(json.dumps(result,indent=2))
    Path("benchmark_results.json").write_text(json.dumps(result,indent=2))
