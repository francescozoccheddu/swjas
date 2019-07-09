# swjas


**Simple WSGI JSON API Server**

### Installation
`pip install swjas`


## Core

### Usage
Call `core.makeApplication` to create your WSGI application.
- **`makeApplication`**
    - **Parameters**
        - `route` : *Iterable*  
        Iterable of `(path, handler)` tuples or lists
            - `path` : `str`  
            Mapped URL path.  
            Do not include scheme, authority, query or fragment.
            - `handler` : *Callable*  
            Object (or function) to call to handle incoming POST requests to `path`.
                - **Parameters**
                    - `data` : `dict`, `list`, `int`, `float`, `string`, `bool` or `None`  
                    Deserialied JSON request body if any, otherwhise `None`
                - **Returns**  
                JSON serializable object or `None`.  
                `datetime.datetime` objects have built-in serialization support.  
                Custom objects can be serialized if they provide a `_json` property that returns a JSON serializable object.
    - **Returns**  
    WSGI application.

### Examples
Serve using `wsgi_ref`
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
Serve using `waitress`
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
Define custom JSON serializable objects
```python
class Point:
    
    def __init__(x, y):
        self.x = x
        self.y = y

    @property
    def _json(self):
        return [self.x, self.y]
```


## Clean

### Usage
Decorate your handlers with the `clean.clean` decorator.
- **`clean`**
    - **Parameters**
        - `field` : `Field`  
        Expected request body scheme.
    - **Returns**  
    Validated and cleaned request body.
    - **Raises**
        - `exceptions.BadRequestException`  
        If the request body does not match the provided scheme.
- **`Field`**
    - **Constructor**
        - **Parameters**
            - `missing` : `Do` or `Default`  
            What to do when this field is missing.
            - `error` : `Do` or `Default`  
            What to do when this field is invalid.
    - **Methods**
        - `clean` *(abstract)*  
            Validate and clean the field.  
            Derived fields must implement it.
            - **Parameters**
                - `value`  
                Deserialized request body value to clean.
            - **Returns**  
            Cleaned value.
            - **Raises**
                - `FieldException`  
                If the value is invalid.
        - `cleanAndAdd`  
            Validate and clean the field. 
            - **Parameters**
                - `present` : `bool`  
                Whether the field is present or not.
                - `value`  
                Deserialized request body value to clean.
                - `add` : *Callable*  
                Object (or function) to call if the field is cleaned.
                    - **Parameters**
                        - `value`  
                        Cleaned value.  
### Examples
Simple cleaning
```python
from swjas.clean import clean, Default, IntField, StringField, FloatField, DictField, ListField

@clean(DictField({
    "a": IntField(min=1),
    "b": IntField(min=1)
}))
def sumPositiveIntegers(data):
    return {
        "sum": data["a"] + data["b"]
    }

@clean(ListField(minLength=1, fields=FloatField()))
def floatAverage(data):
    return sum(data) / len(data)

@clean(DictField({
    "username": StringField(minLength=5, maxLength=20, regex=r"[A-Za-z0-9]+"),
    "password": StringField(minLength=8, maxLength=16, regex=r"[A-Za-z0-9]+"),
    "age": IntField(min=18, max=150, missing=Default(None)),
    "fullName": StringField(minLength=1, maxLength=128, missing=Default(None))
}))
def printMe(data):
    print(data)
    return {
        "success": True
    }
```
Custom field
```python
from swjas.clean import TypeField, FieldException, Do

class EvenNumberField(TypeField):

    def __init__(self, missing=Do.RAISE, error=Do.RAISE):
        super().__init__(int, missing=missing, error=error)

    def clean(self, value):
        value = super().clean(value)
        if value % 2 != 0:
            raise FieldException("Odd number")
        return value
```

## Exceptions
Coming soon...
## Client
Coming soon...