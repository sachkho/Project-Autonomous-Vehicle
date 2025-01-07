import contextlib
import threading
import time
from fastapi import Body, FastAPI
from pydantic import BaseModel
import uvicorn
import requests
import os
import subprocess

class Orchestrator(uvicorn.Server):
    def install_signal_handlers(self):
        pass
    # Allow uvicorn to run in a thread
    @contextlib.contextmanager
    def run_in_thread(self):
        thread = threading.Thread(target=self.run)
        thread.start()
        try:
            while not self.started:
                time.sleep(1e-3)
            yield
        finally:
            self.should_exit = True
            thread.join()

app = FastAPI()

@app.get("/")
async def read_root():
    return {"message": "Hello group 2!"}

# ----------------------------------- Logic ---------------------------------- #

class MarkerMap(BaseModel):
    map: list[int]
    
class RoleList(BaseModel):
    roles: list[str]

@app.get("/ping")
async def get_pinged():
    """Returns the name of the robot to check if he is alive"""
    return {"name": "groupB"}
    
@app.get("/robots-role")
async def test_get_robots_role():
    return {"robots_role": ["teamA","teamB"]}

@app.get("/test")
async def test_get():
    return {"message": "OK"}, 200


def mainloop():
    config = uvicorn.Config(app, host="127.0.0.1", port=5001, log_level="info", reload=True)
    server = Orchestrator(config=config)

    with server.run_in_thread():
        subprocess.Popen(["python3", "orchestrator/main.py", "--params", "test_server_params.json", "--nosocket"])
        
        while True:
            pass

if __name__ == "__main__":
    mainloop()
    