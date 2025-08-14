from tts import speak
import requests
import time
from threading import Thread

host = "https://gentle-buffalo-stirred.ngrok-free.app/"
id = None

def execute(info):
    command = info.get("command")
    extra = info.get("extra")
    print(command)
    print(extra)
    if not command: return
    if command == "tts":
        speak(extra["text"])

def loop():
    while True:
        try:
            response = requests.post(host+f"/get_command", json={"id": id}) 
            print(response.content)
            info = response.json()
            thread = Thread(target=execute, args=(info, ))
            thread.start()
        except Exception as e:
            print(e)
        time.sleep(1)

def main():
    global id
    while not id:
        try:
            id = requests.get(host+"/get_id").json()["id"]
        except:
            print("offline")
    print(id)
    loop()

main()
