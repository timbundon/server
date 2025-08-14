from flask import Flask, request, jsonify, Response
from threading import Thread
import time


ip_to_id = {}
queue = {}
app = Flask(__name__)

@app.route("/get_id")
def get_id():
    ip = request.remote_addr
    if not ip in ip_to_id.keys():
        ip_to_id[ip] = str(len(ip_to_id.keys()))
    if not ip_to_id[ip] in queue.keys():
        queue[ip_to_id[ip]] = []
    return jsonify({"id": ip_to_id[ip]})

@app.route("/add_command", methods=["POST"])
def add_command():
    data = request.get_json()
    id = data.get("id")
    info = data.get("info")
    queue[id].append(info)
    return "OK"

@app.route("/get_command", methods=["POST"])
def get_command():
    id = request.get_json().get("id")
    print(queue)
    if len(queue[id]) == 0:
        return "NO"
    info = queue[id].pop(0)
    return jsonify(info)

app.run("0.0.0.0", port=5000)