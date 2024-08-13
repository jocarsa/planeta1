from flask import Flask, jsonify
import sqlite3

app = Flask(__name__)

def get_max_x_y():
    connection = sqlite3.connect("datos_terreno.db")
    cursor = connection.cursor()

    cursor.execute("SELECT MAX(x), MAX(y) FROM terreno")
    max_x, max_y = cursor.fetchone()

    connection.close()
    return max_x, max_y

@app.route('/npc_positions', methods=['GET'])
def npc_positions():
    connection = sqlite3.connect("datos_terreno.db")
    cursor = connection.cursor()

    max_x, max_y = get_max_x_y()

    cursor.execute("SELECT id, x, y, direction, last_update_epoch FROM npc")
    npc_rows = cursor.fetchall()

    npc_positions = []
    for row in npc_rows:
        npc_id, x, y, direction, last_update_epoch = row
        normalized_x = x / max_x
        normalized_y = y / max_y
        npc_positions.append({
            "id": npc_id,
            "x": normalized_x,
            "y": normalized_y,
            "direction": direction,
            "last_update_epoch": last_update_epoch
        })

    connection.close()
    return jsonify(npc_positions)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
