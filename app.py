import os
import keygen

from flask import Flask, render_template, request
from flask_socketio import SocketIO, send, emit

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET")
socketio = SocketIO(app)

rooms = {} # List of rooms, identified by an id
@app.route('/')
def root():
    return render_template("room.html")

@app.route('/room/<room_id>')
def room_page(room_id):
    if room_id in rooms:
        return render_template('chat.html', room_id=room_id)  # Pass room ID to the chat page
    else:
        return "Room not found", 404

@socketio.on('message')
def handle_message(msg):
    print(f"Message received with content: {msg} and session ID {request.sid}")
    # get the roomId
    room_id = msg.get('roomId')
    if room_id in rooms:
        for connection in rooms[room_id]['connections']:
            emit('message', msg, to=connection['sid'])

@socketio.on('join-room-chat')
def handle_join_room_chat(data):
    print(f"User {request.sid} attempting to join room {data.get('roomId')}")
    room_id = data.get('roomId')
    if room_id in rooms:
        public_key = data.get('publicKey')

        for connection in rooms[room_id]['connections']:
            emit('room-joined-other', public_key, to=connection['sid'])

        rooms[room_id]['connections'] += {'sid': request.sid, 'publicKey': public_key}
        print(f"User {request.sid} joined room {room_id}")
        emit('room-joined-chat', room_id, broadcast=False)
    else:
        emit('room-not-found-chat', room_id, broadcast=False)

@socketio.on('join-room')
def handle_join_room(data):
    room_id = data.get('roomId')
    if room_id in rooms:
        emit('room-joined', room_id, broadcast=False)
    else:
        emit('room-not-found', room_id, broadcast=False)


@socketio.on('room-created')
def handle_room_creation(room_id):
    print(f"Room {room_id} created")

@socketio.on('create-room')
def handle_create_room(data):
    max_users = int(data.get('roomSize', 10))  # Get the max users for the room, default to 10
    room_id = keygen.keygen() # 64 character random key
    rooms[room_id] = {'size': max_users, 'connections': []}  # Initialize the room
    emit('room-created', room_id, broadcast=False)  # Emit back to the creator
    print(f"Room {room_id} created with max size {max_users} and session ID {request.sid}")


if __name__ == '__main__':
    app.run()
