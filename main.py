import requests
import time
from threading import Thread
import pygame
import io

host = "https://gentle-buffalo-stirred.ngrok-free.app/"
id = None

pygame.init()
pygame.mixer.init()

def speak(extra):
    url = None
    text = extra.get("text") or ""
    lang = extra.get("lang") or "eng"
    speed = extra.get("speed") or 100
    pitch = extra.get("pitch") or 75
    if lang == "eng":
        url = f"https://sam.seofernando.com/speak?text={text}&mouth=100&throat=140&speed={speed}&pitch={pitch}"
    else:
        url = f"https://sam.seofernando.com/speak?text={text}&mouth=100&throat=140&speed={speed}&pitch={pitch}"
    responce = requests.get(url)
    sound = io.BytesIO(responce.content)
    pygame.mixer.music.load(sound)
    pygame.mixer.music.play()

def execute(info):
    command = info.get("command")
    extra = info.get("extra")
    print(command)
    print(extra)
    if not command: return
    if command == "tts":
        speak(extra)

def loop():
    while True:
        try:
            response = requests.post(host+f"/get_command", json={"id": id}, headers={"ngrok-skip-browser-warning": "69420"}) 
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
            id = requests.get(host+"/get_id", headers={"ngrok-skip-browser-warning": "69420"}).json()["id"]
        except:
            print("offline")
        time.sleep(10)
    print(id)
    loop()

main()
