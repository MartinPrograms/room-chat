import os
import keygen

from flask import Flask, render_template, request
from flask_socketio import SocketIO, send, emit

import threading

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
        # check if the room is full
        if len(rooms[room_id]['connections']) >= rooms[room_id]['size']:
            return "Room is full", 404
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
            sid = connection.get('sid')
            emit('message', msg, to=sid)

@socketio.on('join-room-chat')
def handle_join_room_chat(data):
    print(f"User {request.sid} attempting to join room {data.get('roomId')}")
    room_id = data.get('roomId')
    if room_id in rooms:
        public_key = data.get('publicKey')

        for connection in rooms[room_id]['connections']:
            emit('room-joined-other', {'publicKey' : public_key, 'sid': request.sid}, to=connection['sid'])

        rooms[room_id]['connections'] += [{'sid': request.sid, 'publicKey': public_key}]
        print(f"User {request.sid} joined room {room_id}")

        # args: roomId, publicKey, shouldGenAES
        # Shoudl gen aes should be true if the user is the first one to join the room
        shouldGenAES = len(rooms[room_id]['connections']) == 1
        emit('room-joined-chat', {'roomId': room_id, 'publicKey': public_key, 'shouldGenAES': shouldGenAES}, broadcast=False)
    else:
        emit('room-not-found-chat', room_id, broadcast=False)

@socketio.on('join-room')
def handle_join_room(data):
    room_id = data.get('roomId')
    if room_id in rooms:
        emit('room-joined', room_id, broadcast=False)
    else:
        emit('room-not-found', room_id, broadcast=False)

@socketio.on('request-aes')
def handle_request_aes(data):
    room_id = data.get('roomId')
    public_key = data.get('publicKey')
    sid = request.sid # the owner who wants to get the AES key
    if room_id in rooms:
        # get the first user in the room, hes the owner
        owner = rooms[room_id]['connections'][0]
        print(f"User {sid} requested AES key for room {room_id} from {owner}")
        ownersid = owner.get('sid')
        emit('request-key', {'publicKey': public_key, 'sid': sid}, to=ownersid)


@socketio.on('return-aes')
def handle_return_aes(data):
    room_id = data.get('roomId')
    sid = data.get('senderId')
    if room_id in rooms:
        for connection in rooms[room_id]['connections']:
            if connection['sid'] == sid:
                emit('return-key', data, to=connection['sid'])

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

connections_to_remove = []
rooms_to_remove = []

@socketio.on('disconnect')
def handle_disconnect():
    print(f"User {request.sid} disconnected")
    for room_id in rooms:
        for connection in rooms[room_id]['connections']:
            if connection['sid'] == request.sid:
                connections_to_remove.append({'room_id': room_id, 'sid': request.sid})
                break
        if len(rooms[room_id]['connections']) == 0:
            rooms_to_remove.append(room_id)

def clear_rooms():
    global connections_to_remove
    while True:
        for connection in connections_to_remove:
            for room in rooms:
                if room == connection['room_id']:
                    rooms[room]['connections'] = [c for c in rooms[room]['connections'] if c['sid'] != connection['sid']]
                    print(f"Removed user {connection['sid']} from room {room}")

        for room in rooms_to_remove:
            del rooms[room]
            print(f"Removed room {room}")

        rooms_to_remove = []
        connections_to_remove = []
        threading.Event().wait(5)

threading.Thread(target=clear_rooms).start()

if __name__ == '__main__':
    app.run()