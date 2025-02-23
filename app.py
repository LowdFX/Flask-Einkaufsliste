from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
from flask_cors import CORS
import sqlite3

app = Flask(__name__)
CORS(app)  # Erlaubt CORS für alle Domains
socketio = SocketIO(app, cors_allowed_origins="*")

# Datenbank initialisieren
def init_db():
    with sqlite3.connect("einkaufsliste.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS einkaufsliste (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                erledigt BOOLEAN DEFAULT 0
            )
        """)
        conn.commit()

init_db()

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/items')
def get_items():
    with sqlite3.connect("einkaufsliste.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, erledigt FROM einkaufsliste ORDER BY erledigt ASC, id ASC")
        items = [{"id": row[0], "name": row[1], "erledigt": bool(row[2])} for row in cursor.fetchall()]
    return jsonify(items)

@app.route('/add', methods=['POST'])
def add():
    name = request.json.get('name')
    if name and name.strip():
        with sqlite3.connect("einkaufsliste.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM einkaufsliste WHERE name = ?", (name.strip(),))
            count = cursor.fetchone()[0]
            
            if count == 0:  # Falls der Eintrag noch nicht existiert, speichern
                cursor.execute("INSERT INTO einkaufsliste (name) VALUES (?)", (name.strip(),))
                conn.commit()
                socketio.emit('update_items')  # WebSocket-Update senden

        return jsonify({"message": "Eintrag hinzugefügt", "name": name}), 200
    return jsonify({"error": "Kein Name angegeben"}), 400


@app.route('/delete/<int:item_id>', methods=['DELETE'])
def delete(item_id):
    with sqlite3.connect("einkaufsliste.db") as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM einkaufsliste WHERE id = ?", (item_id,))
        conn.commit()
    socketio.emit('update_items')  # WebSocket-Update an alle Clients
    return jsonify({"message": f"Artikel {item_id} gelöscht"}), 200


@app.route('/toggle/<int:item_id>', methods=['PUT'])
def toggle(item_id):
    with sqlite3.connect("einkaufsliste.db") as conn:
        cursor = conn.cursor()
        # Status umkehren (1 → 0, 0 → 1)
        cursor.execute("UPDATE einkaufsliste SET erledigt = NOT erledigt WHERE id = ?", (item_id,))
        conn.commit()
        cursor.execute("SELECT erledigt FROM einkaufsliste WHERE id = ?", (item_id,))
        new_status = cursor.fetchone()[0]  # Neuen Status abrufen
    socketio.emit('update_items')  # WebSocket-Benachrichtigung senden
    return jsonify({"message": "Status geändert", "erledigt": bool(new_status)}), 200

@app.route('/delete_all', methods=['DELETE'])
def delete_all():
    with sqlite3.connect("einkaufsliste.db") as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM einkaufsliste")
        conn.commit()
    socketio.emit('update_items')  # WebSocket-Update senden
    return jsonify({"message": "Alle Einträge gelöscht"}), 200


if __name__ == '__main__':
    socketio.run(app, host='127.0.0.1', port=1001, debug=True)
