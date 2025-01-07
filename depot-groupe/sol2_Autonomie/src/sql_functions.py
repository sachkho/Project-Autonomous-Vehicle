import sqlite3
class SQLAuto:
    def __init__(self, dbFile: str = "/dev/shm/orchestrator.db"):
        self.dbFile = dbFile

    # ---------------------------------- Getting --------------------------------- #

    def get_SQL_result(self, command):
        try:
            con = sqlite3.connect(self.dbFile)
            cur = con.cursor()
            res = cur.execute(command).fetchall()
            con.close()
            return res
        except Exception as e:
            print(str(e))
            return False

    def get_construct_robots_role(self) -> list:
        query = "SELECT * FROM ROBOTS"
        result = self.get_SQL_result(query)
        if result == [] :
            return False
        robot_list = ["" for robot in result]
        for robot in result:
            robot_list[robot[2]] = robot[1]
        return robot_list

    def get_construct_marker_map(self) -> list:
        query = "SELECT * FROM MARKER_MAP"
        result = self.get_SQL_result(query)
        if result == [] :
            return 
        marker_map = {}
        # marker_map = { "SO":1, "O":2, "NO":3, "NE":4, "E":5, "SE":6}
        for line in result:
            marker_map[line[2]] = line[1]
        return marker_map 
    
    def get_logic_state(self) -> int:
        query = "SELECT * FROM LOGIC WHERE name = 'STATE'"
        result = self.get_SQL_result(query)
        if result == [] :
            return False
        return result[0][2]
    
    def get_our_role(self) -> int:
        query = "SELECT * FROM LOGIC WHERE name = 'ROLE'"
        result = self.get_SQL_result(query)
        if result == [] :
            return False
        return result[0][2]

    def get_to_check(self) -> int:
        query = "SELECT * FROM MARKER_MAP WHERE position = 'TO_CHECK'"
        result = self.get_SQL_result(query)
        if result == [] :
            return False
        return result[0][2]

    # --------------------------------- Updating --------------------------------- #

    def update_SQL_table(self, command):
        try:
            con = sqlite3.connect(self.dbFile)
            cur = con.cursor()
            cur.execute(command)
            con.commit()
            con.close()
            return command
        except Exception as e:
            print(str(e))
            return False
    
    def set_robot_role(self, robot: str, role: int) -> bool:
        query = f"UPDATE ROBOTS SET role = {role} WHERE name = '{robot}'"
        return self.update_SQL_table(query)

    def set_logic_state(self,state: int) -> bool:
        query = f"UPDATE LOGIC SET state = {state} WHERE name = 'STATE'"
        return self.update_SQL_table(query)

    def set_marker_map(self, marker: int, position: str) -> bool:
        query = f"UPDATE MARKER_MAP SET marker = {marker} WHERE position = '{position}'"
        return self.update_SQL_table(query)

    def set_our_role(self, role: int) -> bool:
        query = f"UPDATE LOGIC SET state = {role} WHERE name = 'ROLE'"
        return self.update_SQL_table(query)
    
    def set_to_check(self, to_check: int) -> bool:
        query = f"INSERT INTO MARKER_MAP (position, marker) VALUES ('TO_CHECK', 0) "
        return self.update_SQL_table(query)