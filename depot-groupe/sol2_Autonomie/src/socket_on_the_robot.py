import json
import socket
import threading
import os

class Socket:
    """Mother class implementing functions relative to Unix Socket    """
    def __init__(self,socket_path:str,logger:str):
        """Initialize Socket
        
        Args:
            socket_path (str): File path to the unix socket
            logger (str): Name of the logger to log to
        """
        self.logger = setup_logger(logger) #Not mandatory, used for logging (see logger.py)
        self.Socket = socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        self.Socket.bind(socket_path)
        self.Socket.listen(1)   # 1 means that we listen to only one connection
        self.connection:socket.socket = None
        # This flag is used to stop the listening thread
        self.should_stop = False
    
    def listen(self):
        self.logger.info("Waiting for unix socket connection") # Not mandatory, used for logging (see logger.py)
        # We may want to increase the timeout to avoid spamming the logs
        self.Socket.settimeout(0.5)
        while not self.should_stop:
            try:
                self.connection,_ = self.Socket.accept()
                return True
            except socket.timeout:
                # This is fine, we just wait again for a connection
                continue
            except Exception as e:
                # This will never happen, except for a critical error
                # We might want to end the whole program at this point
                self.logger.critical(e) # Not mandatory, used for logging (see logger.py)
                self.should_stop = True
                return False

    def stop(self):
        self.should_stop = True
        # We need to close the connection to avoid a deadlock
        if self.connection:
            self.connection.close()
    
    def send(self, response: str):
        pass
    
class OrchestratorSocket(Socket):
    def __init__(self, socket_path: str, logger: str):
        super().__init__(socket_path,logger)
        self.mode = "manual"
        self.max_speed = 1
        self.autonomous = None
        self.switched_mode = False
        
    def interpret(self, data: str):
        """Interpret the data received from the socket
        
        Args:
            data (str): Data received from the socket
        """
        self.logger.debug("Data received: " + data)
        data = json.loads(data)
        
        if data["order"] == "do_map_marker":
            pass
            # TODO: When receivig this, go in middle and map the marker
            # The output is like {"SO":1, "O":2, "NO":3, "NE":4, "E":5, "SE":6}
            # Where number is the marker value and the string is the position
            # Send it back to the orchestrator with order: 
            """
            {
                "order": "map_marker",
                "map": {
                    "SO":1, 
                    "O":2, 
                    "NO":3, 
                    "NE":4, 
                    "E":5, 
                    "SE":6
                }
            }
            """
        elif data["order"] == "update_marker_map":
            pass
            #TODO : When receiving this, update your own value of marker map
            # See main.py for format
        elif data["order"] == "go_to_marker":
            pass
            # TODO: when receiving this, go to the marker and then send reached_marker (No matter how)
            """{"order": "go_to_marker", "marker": marker, "position": self.config.marker_postion[marker], "lastPos": "M"}
            """
            # See main.py for every case
        elif data["order"] == "go_to_end":
            # TODO: when receiving this, go to the end and then send reached_end (No matter how)
            # See main.py for format
            pass
        
    def listen(self):
        """Get data for the control pane of UIControlSocket
        """
        connection_success = Socket.listen(self)
        if not connection_success:
            return
        self.logger.debug("Entering listen")
        while not self.should_stop:
            data = (self.connection.recv(1024)).decode("utf-8")
            # self.logger.debug("Request received: " + data)
            self.interpret(data)
    
    def send(self,response:str):
        self.connection.sendall(response.encode("utf-8")) 
        
        
def inyourmainloop():
    setup_loggers() # Not mandatory, used for logging (see logger.py)
    
    # Use a way to delete old socket files
    for file in Config.socket_paths:
        if os.path.exists(file):
            os.unlink(file)
        
    orchestrator_socket = OrchestratorSocket(Config.data_socket_path, "Orchestrator") # 1st one is the socket file path 2nd is the name of the logger
    
    orchestrator_socket.logger.debug("Thread Listening") # Not mandatory, used for logging (see logger.py)
    orchestrator_threading = threading.Thread(target=orchestrator_socket.listen, args=())
    orchestrator_socket.start()

    # List of early exit flags
    # 0     normal exit
    # -1    CTRL-C catched
    # -2    division by zero
    early_exit_flag = 0
    while True:
        try:
            # This is your main loop... Used to catch CTRL-C and other exceptions... It is not mandatory
            break
        except KeyboardInterrupt:
            early_exit_flag = -1
            break
        except Exception as e:
            brain_logger.error(e) # Log error
            # TODO: Don't raise in production, continue instead
            raise e
            continue

    if not early_exit_flag:
        brain_logger.debug("The program exited normally")
    else:
        brain_logger.warning(f"The program exited early with code ({early_exit_flag})")

    orchestrator_socket.stop()
    orchestrator_threading.join()
    for file in Config.socket_paths:
        if os.path.exists(file):
            os.unlink(file)
    exit(0)