import requests

url = "https://gentle-buffalo-stirred.ngrok-free.app/"
data = {"info": {"command": "tts", "extra": {"text": "hello comrade how are you", "lang": "eng", "speed": 100}}, "id": "0"}
requests.post(url+"/add_command", json=data)