# swjas
**Simple WSGI JSON API Server**
### Installation
`pip install swjas`
## Core
### Usage
Call `core.makeApplication` to create your WSGI application.
It takes a list of `(path, handler)` tuples or lists as only parameter.
`path` must be a string and `handler` a callable taking the deserialized JSON request body as only parameter.
### Examples
Using `wsgi_ref`
```python
from wsgiref.simple_server import make_server
from swjas.core import makeApplication

# Services

def authentication(data):
    authenticated = data["username"] == "Francesco" and data["password"] == "12345"
    return {
        "authenticated": authenticated
    }

def intDivision(data):
    if data["b"] == 0:
        return {
            "error": "Division by zero"
        }
    return {
        "quotient": data["a"] // data["b"],
        "remainder": data["a"] % data["b"]
    }

# Server

if __name__ == "__main__":
    routes = [
        ('auth', authentication),
        ('idiv', intDivision)
    ]
    server = make_server("localhost", 8000, makeApplication(routes))
    server.serve_forever()
```
Using `waitress`
```python
import waitress
from swjas.core import makeApplication
import random, string

# Services

def generateRandomID(data):
    id = ""
    for _ in range(data["length"]):
        id += random.choice(string.ascii_letters)
    return {
        "id": id
    }

# Server

if __name__ == "__main__":
    routes = [
        ('genid', generateRandomID)
    ]
    waitress.serve(makeApplication(routes), listen='*:8000')
```
## Clean
Coming soon...
## Exceptions
Coming soon...
## Client
Coming soon...