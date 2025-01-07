import sqlite3
import json
from typing import Union
import os

from sys import path
path.append(os.path.join(os.path.dirname(__file__),".."))
from logger import setup_logger,setup_loggers
from sql_functions import SQLAuto

# ---------------------------------------------------------------------------- #
#                                    Config                                    #
# ---------------------------------------------------------------------------- #

class Config:
    socket_path = "orchestrator.sock"
    
    def __init__(self, file : str = "server_params.json"):
        params = json.load(open(file))
        self.name : str = params["name"]
        
        self.dbFile : str = params["dbFile"]
        self.SQL = SQLAuto(self.dbFile)
        self.dbLogger = setup_logger("DataBase")
        
        self.robot_list : Union[dict,None] = params["robot_list"]
        self.robot_priority : list[str] = params["robot_priority"]
        
        self.map_robot_marker : Union[dict,list] = params["map_robot_marker"]
        self.marker_postion = params["marker_position"]


config = Config(file="sol2_Autonomie/src/test_server_params.json")

if os.path.isfile(config.dbFile):
        os.unlink(config.dbFile)

config.SQL.update_SQL_table("CREATE TABLE IF NOT EXISTS ROBOTS (id INTEGER PRIMARY KEY, name TEXT, role INTEGER)")
i = 0
for robot in config.robot_list.keys():
    config.SQL.update_SQL_table(f"INSERT INTO ROBOTS (name, role) VALUES ('{robot}', '{i}') ")
    i += 1
    
print(config.SQL.get_construct_role_list())