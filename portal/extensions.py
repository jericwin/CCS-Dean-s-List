from flask_socketio import SocketIO

# Same-origin only (Flask-SocketIO's default); async mode picked automatically (threading).
socketio = SocketIO()
