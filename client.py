import requests

response = requests.post("http://127.0.0.1:5000/login/")


print(response.text)
