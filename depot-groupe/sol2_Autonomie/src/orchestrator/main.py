import asyncio
from typing import List, Optional, Union, Annotated
import threading
import json
import time
import socket
import os
import logging
import requests
import argparse

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
        self.objectives : list[list] = params["objectives"]
        
    def SQL_Log(self, returned: str):
        self.dbLogger.debug("Executed: " + returned)

# ---------------------------------------------------------------------------- #
#                           UNIX Socket to the robot                           #
# ---------------------------------------------------------------------------- #

class ClientSocket:
    """Client class for UNIX Socket used multiple times"""
    
    def __init__(self, socket_path: str, logger: str):
        """Constructor for ClientSocket class

        Args:
            socket_path (str): path to the file for the UNIX Socket
            logger (str): Name for the logger (from logging)
        """
        self.logger = setup_logger(logger)
        self.Socket = socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        self.Socket.connect(socket_path)
        self.connection:socket.socket = None
        # This flag is used to stop the listening thread
        self.should_stop = False
        while not (os.path.exists(socket_path)):
            pass  # While the socket server doesn't exist
        self.logger.info("Connected to UNIX Socket")
        self.should_stop = False
        
    # -------------------------------- interpret() ------------------------------- #
        self.marker_map : dict = None
        # Type: {"SO":1, "O":2, "NO":3, "NE":4, "E":5, "SE":6}
        
    def interpret(self, data: str):
        """Understanding what's going on on the socket
        """
        data = json.loads(data)
        # TODO: Send this when your robot have done the mapping
        if data["order"] == "map_marker":
            self.marker_map = data["map"]
            self.logger.info("Received marker map")
        # TODO: send this when your robot have reached a marker
        elif data["order"] == "reached_marker":
            self.marker_reached = True
            self.logger.info("Marker reached")
        # TODO: send this when your robot have reached the end
        elif data["order"] == "reached_end":
            self.end_reached = True
            self.logger.info("End reached")
        # TODO: send this when your robot has detected a collision
        elif data["order"] == "ally_inbound":
            self.ally_inbound = True
            self.viewed_marker = data["collision_marker"]
            self.logger.info("Ally inbound")
        
    def stop(self):
        self.should_stop = True
        # We need to close the connection to avoid a deadlock
        if self.connection:
            self.connection.close()        

    def listen(self):
        """Get data sent on the UNIX Socketx
        """
        self.logger.debug("Entering listen")
        while not self.should_stop:
            data = (self.connection.recv(1024)).decode("utf-8")
            self.interpret(data)   
            
    def send(self, request: str):
        self.Socket.sendall((request + "\n").encode("utf-8"))
            
# ---------------------------------------------------------------------------- #
#                                  Game Logic                                  #
# ---------------------------------------------------------------------------- #

class Logic:
    ST_INIT = 0
    ST_ELECT_ROBOT = 1  
    ST_COMPARE_ROBOTS_ROLE = 2
    ST_UPDATING_OUR_ROLE = 3
    ST_WAITING_FOR_MAP = 4
    ST_WAITING_OTHER_REACH = 5
    ST_SIGNALING_OTHER = 6
    ST_DOING_PARKOUR = 7
    ST_REACHING_END = 8
    ST_REACHED_END = 9
    
    ST_MAPPING_MARKER = 10
    ST_SENDING_MARKER_MAP = 11
    ST_ERROR_MAPPING = 12
    
    ST_REDO_ELECT_ROBOT = 100
    
    ST_DO_NOTHING = -1
    
    def __init__(self, orchestrator_socket: ClientSocket, config: Config):
        self.logger = setup_logger("Logic")
        self.lastInstructionTime = 0.0
        self.currentTime = 0.0
        self.currentDeltaTimeWait = 0.0
        self.currentState = Logic.ST_INIT
        self.oSock : ClientSocket = orchestrator_socket
        self.config : Config = config
        self.our_role = -1
        
        # ------------------------------- elect_robot() ------------------------------ #
        self.er_list=self.config.robot_priority.copy()
        self.er_robot_role_index = 0
                
        # --------------------------- compare_robots_role() -------------------------- #
        self.crr_list = self.config.SQL.get_construct_robots_role()
        
        # ----------------------------- mapping_marker() ----------------------------- #
        self.mm_timeout_started = False
        
        # ----------------------------- sending_marker() ----------------------------- #
        self.sm_list = self.config.SQL.get_construct_robots_role()
        
        # ------------------------------ doing_parkour() ----------------------------- #
        self.dp_marker_list = None
        self.dp_is_1st_marker = False
        
        # ----------------------------- waiting_for_map() ---------------------------- #
        self.wfm_timeout_started = False
        
    
    def change_state(self, state: int):
        self.logger.info(f"Changing state from {self.currentState} to {state}")
        self.currentState = state
        self.config.SQL_Log(self.config.SQL.set_logic_state(state))
    
    def elect_robot(self):
        if len(self.er_list) == 0:
            if self.currentTime - self.lastInstructionTime > self.currentDeltaTimeWait:
                self.change_state(Logic.ST_COMPARE_ROBOTS_ROLE)
        else:
            robot = self.er_list[0]
            try:
                r = requests.get(f"http://{self.config.robot_list[robot]}/ping", timeout=2)
            except requests.exceptions.ReadTimeout:
                self.logger.warning(f"Robot {robot} is not responding")
            else:
                if r.status_code == 200:
                    self.logger.info(f"Robot {robot} is alive")
                    self.config.SQL_Log(self.config.SQL.set_robot_role(robot, self.er_robot_role_index))
                    self.er_robot_role_index += 1
                    self.er_list.pop(0)
            if len(self.er_list) == 0:
                self.currentDeltaTimeWait = 2.0
                self.lastInstructionTime = self.currentTime

    def compare_robots_role(self):
        if len(self.crr_list) == 0:
            if self.currentTime - self.lastInstructionTime > self.currentDeltaTimeWait:
                self.change_state(Logic.ST_UPDATING_OUR_ROLE)
        else:
            robot = self.crr_list[0]
            try:
                robots_role = self.config.SQL.get_construct_robots_role()
                r = requests.get(f"http://{self.config.robot_list[robot]}/robots-role", timeout=5)
            except requests.exceptions.ReadTimeout:
                self.logger.warning(f"Robot {robot} is not responding")
                self.change_state(Logic.ST_REDO_ELECT_ROBOT) # TODO
            else:
                if r.status_code == 200:
                    print(r.json())
                    robots_role_r = r.json()["robots_role"]
                    if robots_role != robots_role_r:
                        self.logger.info(f"Robot {robot} has different roles")
                        self.change_state(Logic.ST_REDO_ELECT_ROBOT)
                    else:   
                        self.logger.info(f"Robot {robot} has same roles")
                        self.crr_list.pop(0)
            if len(self.crr_list) == 0:
                self.currentDeltaTimeWait = 2.0
                self.lastInstructionTime = self.currentTime
        
    def updating_our_role(self):
        role : int = self.config.SQL.get_construct_robots_role().index(self.config.name)
        self.config.SQL_Log(self.config.SQL.set_our_role(role))
        self.our_role = role
        if role == 0:
            self.change_state(Logic.ST_MAPPING_MARKER)
        else:
            self.change_state(Logic.ST_WAITING_FOR_MAP)
    
    def mapping_marker(self):
        if not(self.mm_timeout_started):
            self.mm_timeout_started = True
             # TODO: When receivig this, go in middle and map the marker
            # The output is like {"SO":1, "O":2, "NO":3, "NE":4, "E":5, "SE":6}
            # Where number is the marker value and the string is the position
            self.oSock.send(json.dumps({"order": "do_map_marker"}))
            self.currentDeltaTimeWait = 90.0
            self.lastInstructionTime = self.currentTime
            
        if (self.mm_timeout_started):
            if self.currentTime - self.lastInstructionTime > self.currentDeltaTimeWait:
                self.change_state(Logic.ST_ERROR_MAPPING)
            else:
                if self.oSock.marker_map != None:
                    for position in self.oSock.marker_map.keys():
                        self.config.SQL_Log(self.config.SQL.set_marker_map(self.oSock.marker_map[position], position))
                    self.change_state(Logic.ST_SENDING_MARKER_MAP)
    
    def sending_marker(self):
        if len(self.sm_list) == 0:
            if self.currentTime - self.lastInstructionTime > self.currentDeltaTimeWait:
                self.change_state(Logic.ST_DOING_PARKOUR)
        else:
            robot = self.sm_list[0]
            try:
                marker_map = self.config.SQL.get_construct_marker_map()
                r = requests.get(f"http://{self.config.robot_list[robot]}/post-marker-map", 
                                 json=json.dumps(marker_map), timeout=5)
            except requests.exceptions.ReadTimeout:
                self.logger.warning(f"Robot {robot} is not responding")
                self.change_state(Logic.ST_REDO_ELECT_ROBOT)
            else:
                if r.status_code == 200:   
                    self.logger.info(f"Markers sent to {robot}")
                    self.sm_list.pop(0)
            if len(self.sm_list) == 0:
                self.currentDeltaTimeWait = 3.0
                self.lastInstructionTime = self.currentTime
    
    def waiting_for_map(self):
        is_to_check = self.config.SQL.get_to_check()
        
        if not(self.wfm_timeout_started):
            self.wfm_timeout_started = True
            self.currentDeltaTimeWait = 90.0
            self.lastInstructionTime = self.currentTime
        
        elif is_to_check != 0:
            self.marker_map = self.config.SQL.get_construct_marker_map()
            #TODO : When receiving this, update your own value of marker map
            self.oSock.send(json.dumps({"order": "update_marker_map", "map": self.marker_map}))
            self.change_state(Logic.ST_WAITING_OTHER_REACH)
        
        elif self.currentTime - self.lastInstructionTime > self.currentDeltaTimeWait:
            self.change_state(Logic.ST_REDO_ELECT_ROBOT)
    
    def waiting_other_reach(self):
        # Doing nothing because we don't have to
        pass
    
    def doing_parkour(self):
        if self.dp_marker_list == None:
            self.dp_marker_list = self.config.objectives[self.our_role]
            marker = self.dp_marker_list[0]
            if self.our_role == 0:
                # TODO: when receiving this, go to the marker and then send reached_marker (No matter how)
                self.oSock.send(json.dumps({"order": "go_to_marker", "marker": marker, "position": self.config.marker_postion[marker], "lastPos": "M"}))
            else:
                self.oSock.send(json.dumps({"order": "go_to_marker", "marker": marker, "position": self.config.marker_postion[marker], "lastPos": "S"}))
            self.dp_last_pos = self.config.marker_postion[marker]
            self.dp_marker_list.pop(0)
            self.dp_is_1st_marker = True
        
        elif len(self.dp_marker_list) > 0 and self.oSock.marker_reached:
            if self.dp_is_1st_marker:
                self.change_state(Logic.ST_SIGNALING_OTHER)
            self.oSock.marker_reached = False
            marker = self.dp_marker_list[0]
            self.oSock.send(json.dumps({"order": "go_to_marker", "marker": marker, "position": self.config.marker_postion[marker], "lastPos": self.dp_last_pos}))
            self.dp_last_pos = self.config.marker_postion[marker]
            self.dp_marker_list.pop(0)
        
        elif len(self.dp_marker_list) == 0 and self.oSock.marker_reached:
            self.oSock.marker_reached = False
            # TODO: when receiving this, go to the end and then send reached_end (No matter how)
            self.oSock.send(json.dumps({"order": "go_to_end"}))
            self.change_state(Logic.ST_REACHING_END)
    
    def signaling_other(self):
        robot_role = self.config.SQL.get_construct_robots_role()
        if len(robot_role) > self.our_role + 1:
            nextRobot = robot_role[self.our_role + 1]
            nextRobotIP = self.config.robot_list[nextRobot]
            r = requests.get(f"http://{nextRobotIP}/previous-robot-reached", timeout=5)
            if r.status_code == 200:
                self.dp_is_1st_marker = False
                self.change_state(Logic.ST_DOING_PARKOUR)
        else:
            self.dp_is_1st_marker = False
            self.change_state(Logic.ST_DOING_PARKOUR)
    
    def reaching_end(self):
        # Doing nothing because we don't have to for now
        pass
    

def logic_loop(orchestrator_socket: ClientSocket, orchestrator_logger: logging.Logger):
    last_health_check_time = time.time()
    logic = Logic(orchestrator_socket, config)
    logic.change_state(Logic.ST_INIT)
    
    while True:
        logic.currentState = logic.config.SQL.get_logic_state()
        current_time = time.time()
        if current_time>last_health_check_time:
            last_health_check_time = current_time
            logic.currentTime = current_time
        # ------------------------------ Check collision ----------------------------- #
        if logic.oSock.ally_inbound:
            logic.oSock.ally_inbound = False
            # TODO Check for collisions
        # ---------------------------------- States ---------------------------------- #
        if logic.currentState == Logic.ST_INIT:
            logic.er_list=logic.config.robot_priority.copy()
            logic.currentState = Logic.ST_ELECT_ROBOT
        elif logic.currentState == Logic.ST_ELECT_ROBOT:
            logic.elect_robot()
        elif logic.currentState == Logic.ST_COMPARE_ROBOTS_ROLE:
            logic.compare_robots_role()
        elif logic.currentState == Logic.ST_UPDATING_OUR_ROLE:
            logic.updating_our_role()
        elif logic.currentState == Logic.ST_MAPPING_MARKER:
            logic.mapping_marker()
        elif logic.currentState == Logic.ST_WAITING_FOR_MAP:
            logic.waiting_for_map()
        elif logic.currentState == Logic.ST_SENDING_MARKER_MAP:
            logic.sending_marker()
        elif logic.currentState == Logic.ST_DOING_PARKOUR:
            logic.doing_parkour()
        elif logic.currentState == Logic.ST_WAITING_OTHER_REACH:
            logic.waiting_other_reach()
        elif logic.currentState == Logic.ST_SIGNALING_OTHER:
            logic.signaling_other()
        elif logic.currentState == Logic.ST_REACHING_END:
            logic.reaching_end()
        elif logic.currentState == Logic.ST_REACHED_END:
            logic.change_state(Logic.ST_DO_NOTHING)
        elif logic.currentState == Logic.ST_REDO_ELECT_ROBOT:
            # TODO
            pass
        

# ---------------------------------------------------------------------------- #
#                                   mainloop                                   #
# ---------------------------------------------------------------------------- #

def mainloop(params_file: str, no_socket: bool):
    setup_loggers()
    orchestrator_logger = setup_logger("Orchestrator")
    orchestrator_logger.info("Starting Orchestrator")
    
    global config
    config = Config(file=params_file)

    # -------------------------- Database initialization ------------------------- #
    
    if os.path.isfile(config.dbFile):
        os.unlink(config.dbFile)
    config.SQL.update_SQL_table("CREATE TABLE IF NOT EXISTS MARKER_MAP (id INTEGER PRIMARY KEY, position TEXT, marker INTEGER)")
    for pos in config.marker_postion:
        config.SQL.update_SQL_table(f"INSERT INTO MARKER_MAP (position, marker) VALUES ('{pos}', 0) ")
    config.SQL.set_to_check(0)    
    
    config.SQL.update_SQL_table("CREATE TABLE IF NOT EXISTS ROBOTS (id INTEGER PRIMARY KEY, name TEXT, role INTEGER)")
    i = 0
    for robot in config.robot_list.keys():
        config.SQL.update_SQL_table(f"INSERT INTO ROBOTS (name, role) VALUES ('{robot}', '{i}') ")
        i += 1
        
    config.SQL.update_SQL_table("CREATE TABLE IF NOT EXISTS LOGIC (id INTEGER PRIMARY KEY, name TEXT, state INTEGER)")
    config.SQL.update_SQL_table(f"INSERT INTO LOGIC (name, state) VALUES ('STATE', '{Logic.ST_INIT}') ")
    config.SQL.update_SQL_table(f"INSERT INTO LOGIC (name, state) VALUES ('ROLE', '0') ")
    
    # ---------------------- Logic and socket initialization --------------------- #
    
    if not(no_socket):
        while not(os.path.exists(Config.socket_path)):
            pass
        orchestrator_socket = ClientSocket(Config.socket_path, "Orchestrator")
        
        # Start the listening thread
        orchestrator_socket.logger.debug("Thread Listening")
        orchestrator_listening = threading.Thread(target=orchestrator_socket.listen)
        orchestrator_listening.start()
    else:
        orchestrator_socket = None
        orchestrator_listening = None
        
        # List of early exit flags
        # 0     normal exit
        # -1    CTRL-C catched
        early_exit_flag = 0
        while True:
            try:
                logic_loop(orchestrator_socket,orchestrator_logger)
                break
            except KeyboardInterrupt:
                early_exit_flag = -1
                break
            except Exception as e:
                orchestrator_logger.error(e)    
                # TODO: Don't raise in production, continue instead
                raise e
                continue

    if not early_exit_flag:
        orchestrator_logger.debug("The program exited normally")
    else:
        orchestrator_logger.warning(f"The program exited early with code ({early_exit_flag})")

    orchestrator_socket.stop()
    orchestrator_listening.join()
    exit(0)
    

if __name__ == "__main__":
    # ---------------------------------- parser ---------------------------------- #
    parser = argparse.ArgumentParser(description="Orchestrator")
    parser.add_argument("--params", type=str, default="server_params.json", help="Path to the parameters file")
    parser.add_argument("--nosocket", action=argparse.BooleanOptionalAction, help="Don't use UNIX Socket")
    args = parser.parse_args()
    
    params_file = os.path.join(os.path.dirname(__file__),"..", args.params)
    global config
    config = Config(file=params_file)
    
    mainloop(params_file, args.nosocket)
    