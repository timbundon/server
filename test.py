import requests

url = "https://gentle-buffalo-stirred.ngrok-free.app/"
data = {"info": {"command": "tts", "extra": {"text": "аба"}}, "id": "0"}
requests.post(url+"/add_command", json=data)