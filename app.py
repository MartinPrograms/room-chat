import os

from flask import Flask, render_template
from flask_socketio import SocketIO, send

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET")
socketio = SocketIO(app)

@app.route('/')
def hello_world():  # put application's code here
    return render_template("chat.html")

@socketio.on('message')
def handle_message(msg):
    print(f"Message received: {msg}")
    send(msg, broadcast=True)  # Broadcast the message to all connected clients


if __name__ == '__main__':
    app.run()
