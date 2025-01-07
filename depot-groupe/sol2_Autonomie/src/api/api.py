import sqlite3
from fastapi import Body, FastAPI, Query, Response
from typing import List, Optional, Union, Annotated
from pydantic import BaseModel
import uvicorn
import os
import json

from sys import path
path.append(os.path.join(os.path.dirname(__file__),".."))
from logger import setup_logger,setup_loggers
from sql_functions import SQLAuto
from orchestrator.main import Logic

class Config:
    
    def __init__(self, file: str = "server_params.json"):
        setup_loggers()
        self.apiLogger = setup_logger("API")
        self.dbLogger = setup_logger("DataBaseAPI")
        
        params = json.load(open(file))
        
        self.dbFile : str = params["dbFile"]
        self.SQL = SQLAuto(self.dbFile)
        
        self.name : str = params["name"]
        
# ---------------------------------------------------------------------------- #
#                               Orchestrator API                               #
# ---------------------------------------------------------------------------- #

if __name__ != "__main__":
    default_params_file = "server_params.json"
    params_file = os.path.join(os.path.dirname(__file__),"..", default_params_file)
    config = Config()
    
app = FastAPI()

@app.get("/")
async def read_root():
    return {"message": "Hello group 2!"}

# ------------------------------ Preparing Game ------------------------------ #

class MarkerMap(BaseModel):
    map: dict[str, int]
    
class RoleList(BaseModel):
    roles: list[str]

@app.get("/ping")
async def get_pinged():
    global config
    """Returns the name of the robot to check if he is alive"""
    return {"name": config.name}
    
@app.get("/robots-role")
async def get_robots_role(response : Response):
    robots_role = config.SQL.get_construct_robots_role() 
    response.status_code = 200
    return {"robots_role": robots_role}    
    
@app.get("/redo-elect-robot")
async def get_redo_elect_robot():
    """Tell a robot to redo the elect robot"""
    config.SQL.set_logic_state(Logic.ST_REDO_ELECT_ROBOT)
    return {"message": "OK"}


@app.post("/post-marker-map")
async def post_marker_map(marker_map: Annotated[MarkerMap, Body()]):
    """Tell a robot what is the current marker map"""
    if marker_map:
        for pos in marker_map.keys():
            config.SQL.set_marker_map(pos, marker_map[pos])
        config.SQL.set_marker_map("TO_CHECK", 1)
        return {"message": "OK"}
    else:
        return {"message": "Missing marker map"}, 400
    
@app.get("/previous-robot-reached")
async def get_previous_robot_reached():
    """Tell a robot that the previous robot has reached the goal"""
    config.SQL.set_logic_state(Logic.ST_DOING_PARKOUR)
    return {"message": "OK"}

# -------------------------------- Collisions -------------------------------- #
@app.post("/collision/seen")
async def post_collision_seen():
    """Tell a robot that he has seen a collision"""
    return {"message": "OK"}

# ------------------------------- Human Control ------------------------------ #
@app.get("/human-control/start")
async def get_human_control_start():
    """Start the robot array"""
    return {"message": "OK"}

if __name__ == "__main__":
    # global config
    # config = Config()
    uvicorn.run("api:app", host="0.0.0.0", port=5000, reload=True)
    