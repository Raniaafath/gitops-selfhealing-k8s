from fastapi import FastAPI, Response
from prometheus_fastapi_instrumentator import Instrumentator
import time

app = FastAPI()
start_time = time.time()
is_healthy = True

Instrumentator().instrument(app).expose(app)

@app.get("/")
def root():
    return {"status": "ok", "service": "gitops-selfhealing-demo", "version": "v2"}

@app.get("/health")
def health(response: Response):
    if not is_healthy:
        response.status_code = 500
    return {"healthy": is_healthy}

@app.post("/break-health")
def break_health():
    global is_healthy
    is_healthy = False
    return {"healthy": is_healthy}

@app.get("/metrics-info")
def metrics():
    uptime = time.time() - start_time
    return {"uptime_seconds": round(uptime, 2)}