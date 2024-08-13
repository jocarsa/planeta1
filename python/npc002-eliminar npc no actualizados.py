import sqlite3
import random
import time

# Step 1: Set up the Database Schema
def create_npc_table():
    connection = sqlite3.connect("datos_terreno.db")
    cursor = connection.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS npc (
            id INTEGER PRIMARY KEY,
            x INTEGER,
            y INTEGER,
            direction TEXT,
            last_update_epoch INTEGER
        )
    ''')

    connection.commit()
    connection.close()

create_npc_table()

# Step 2: Object-Relational Conversion (NPC Class)
class NPC:
    def __init__(self, npc_id, x, y, direction, last_update_epoch):
        self.npc_id = npc_id
        self.x = x
        self.y = y
        self.direction = direction
        self.last_update_epoch = last_update_epoch

    def save_to_db(self, cursor):
        cursor.execute('''
            INSERT OR REPLACE INTO npc (id, x, y, direction, last_update_epoch)
            VALUES (?, ?, ?, ?, ?)
        ''', (self.npc_id, self.x, self.y, self.direction, self.last_update_epoch))

    @staticmethod
    def load_from_db(npc_id, cursor):
        cursor.execute('''
            SELECT id, x, y, direction, last_update_epoch FROM npc WHERE id = ?
        ''', (npc_id,))
        row = cursor.fetchone()
        if row:
            return NPC(*row)
        else:
            return None

# Step 3: NPC Movement Logic
def move_npc(npc, cursor, terrain_width, terrain_height, level_water):
    directions = {
        "norte": (0, -1),
        "sur": (0, 1),
        "este": (1, 0),
        "oeste": (-1, 0)
    }

    direction_options = ["norte", "sur", "este", "oeste"]
    random.shuffle(direction_options)

    for direction in direction_options:
        dx, dy = directions[direction]
        new_x = (npc.x + dx) % terrain_width
        new_y = (npc.y + dy) % terrain_height

        cursor.execute("SELECT altura FROM terreno WHERE x = ? AND y = ?", (new_x, new_y))
        result = cursor.fetchone()
        if result and result[0] >= level_water:
            npc.x = new_x
            npc.y = new_y
            npc.direction = direction
            npc.last_update_epoch = int(time.time())
            return npc
    return npc

# Step 4: Main Loop for Updating NPCs
def main_loop():
    connection = sqlite3.connect("datos_terreno.db")
    cursor = connection.cursor()

    terrain_width, terrain_height = 2048*4, 1024*4
    level_water = 32768

    while True:
        cursor.execute("SELECT id FROM npc")
        npc_ids = cursor.fetchall()

        current_time = int(time.time())

        for npc_id in npc_ids:
            npc = NPC.load_from_db(npc_id[0], cursor)
            if npc:
                if current_time - npc.last_update_epoch > 60:
                    # Elimina NPC si no se ha actualizado en más de 60 segundos
                    cursor.execute("DELETE FROM npc WHERE id = ?", (npc_id[0],))
                else:
                    npc = move_npc(npc, cursor, terrain_width, terrain_height, level_water)
                    npc.save_to_db(cursor)

        connection.commit()
        time.sleep(1)

    connection.close()

# Step 5: Initializing and Populating the Database with NPCs
def initialize_npcs(num_npcs=30):
    connection = sqlite3.connect("datos_terreno.db")
    cursor = connection.cursor()

    terrain_width, terrain_height = 2048*4, 1024*4
    level_water = 32768

    for npc_id in range(1, num_npcs + 1):
        while True:
            x = random.randint(0, terrain_width - 1)
            y = random.randint(0, terrain_height - 1)

            cursor.execute("SELECT altura FROM terreno WHERE x = ? AND y = ?", (x, y))
            result = cursor.fetchone()
            if result and result[0] >= level_water:
                direction = random.choice(["norte", "sur", "este", "oeste"])
                npc = NPC(npc_id, x, y, direction, int(time.time()))
                npc.save_to_db(cursor)
                break

    connection.commit()
    connection.close()

initialize_npcs()

# Run the main loop
if __name__ == "__main__":
    main_loop()
