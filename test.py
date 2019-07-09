from swjas import core
from waitress import serve

def handler(data):
    return {
        "success": True
    }

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    serve(core.makeApplication([("test",handler)]), listen="*:8080")