from swjas.client import RequestErrorException, request
import urllib
data = {
    "username": "Francesco",
    "password": 12345
}

try:
    res = request("localhost:8080/signup", data)
except RequestErrorException as e:
    print(f"{e.statusCode}: {e.statusMessage}")
    print(e.data)
except Exception:
    print("Request failed")
