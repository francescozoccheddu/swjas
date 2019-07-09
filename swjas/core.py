from urllib import parse as urlparse
import json
from . import exceptions
import logging
from datetime import datetime

_logger = logging.getLogger("swjas")


def _cleanRoute(route):
    if (not isinstance(route, (tuple, list))) or len(route) != 2:
        raise TypeError("route must be a two-element tuple or list")
    path, handler = route
    if not isinstance(path, str):
        raise TypeError("route path must be a string")
    if not hasattr(handler, '__call__'):
        raise TypeError("route handler must be callable")
    url = urlparse.urlparse(path)
    if not url.path:
        raise ValueError("route path must be a valid network path")
    if any([url.scheme, url.netloc, url.fragment, url.query, url.params]):
        raise ValueError("route path cannot contain scheme, netloc or parameters infos")
    return (url.path.strip("/"), handler)


class JSONEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, "_json"):
            return obj._json
        return json.JSONEncoder.default(self, obj)


def makeApplication(routes):
    # TODO Add docs
    # Prepare route dict
    routeDict = {}
    for path, handler in routes:
        routeDict[path] = handler

    def application(environ, startResponse):
        allowPost = True
        # Catch HTTP exceptions
        try:
            path = environ.get("PATH_INFO", "")
            if path.startswith("/") or path.startswith("\\"):
                path = path[1:]
            if path.endswith("/") or path.endswith("\\"):
                path = path[:-1]
            # Ensure JSON accepted
            # TODO Check 'Accept' header
            # Collect accepted charsets
            # TODO Check 'Accept-Charset' header
            # Collect accepted encoding types
            acceptedEncoding = []
            acceptEncodingHeader = environ.get("HTTP_ACCEPT_ENCODING")
            if acceptEncodingHeader:
                # TODO Parse
                pass
            # Ensure POST method
            method = environ.get("REQUEST_METHOD")
            if method != "POST":
                _logger.info(f"Rejected request to '{path}' with method '{method}'")
                raise exceptions.HttpException.build(405, "Method Not Allowed")
            # Ensure no query
            query = environ.get("QUERY_STRING", "").strip()
            if query != "":
                allowPost = False
                _logger.info(f"Rejected request to '{path}' with query '{query}'")
                raise exceptions.BadRequestException("Unexpected query")
            # Find handler
            handler = routeDict.get(path)
            if handler:
                # Parse request JSON body
                try:
                    requestBodyLength = int(environ.get('CONTENT_LENGTH', 0))
                    requestBody = environ['wsgi.input'].read(requestBodyLength)
                except:
                    requestBody = ""
                # Decode body
                # TODO Check 'Content-Type' header
                # TODO Check 'Content-Encoding' header
                if requestBody == "" or requestBody.isspace():
                    jsonRequestBody = None
                else:
                    try:
                        jsonRequestBody = json.loads(requestBody)
                    except json.JSONDecodeError as e:
                        _logger.info(f"Rejected request to '{path}' with non-JSON data")
                        raise exceptions.HttpException.build(415, "Unsupported Media Type") from exceptions.JSONDecodeException(e)
                # Call handler
                try:
                    jsonResponseBody = handler(jsonRequestBody)
                    if jsonResponseBody is None:
                        responseBody = None
                    else:
                        try:
                            responseBody = json.dumps(jsonResponseBody, cls=JSONEncoder)
                        except:
                            _logger.exception("Error while encoding JSON response")
                            raise
                except exceptions.HttpException as e:
                    # Handler raised a HTTP exception
                    _logger.info(f"Rejected request to '{path}':\n{e}")
                    raise e
                except Exception as e:
                    _logger.exception(f"Exception while processing request to '{path}'")
                    raise exceptions.ServerErrorException("Error while processing the request")
                else:
                    statusCode = 200
                    statusMessage = "OK"
            else:
                # No handler found
                allowPost = False
                _logger.info(f"Rejected request to unrouted path '{path}'")
                raise exceptions.NotFoundException("Invalid path")
        except exceptions.HttpException as e:
            # Prepare HTTP exception response
            def errorize(json):
                return {"error": json}

            try:
                statusCode = e.statusCode
                statusMessage = e.statusMessage
                responseBody = json.dumps(errorize(e), cls=JSONEncoder)
            except:
                _logger.exception("Error while preparing JSON response for HttpException")
                fallbackException = exceptions.ServerErrorException("Error while collecting information about a previous error")
                statusCode = fallbackException.statusCode
                statusMessage = fallbackException.message
                responseBody = json.dumps(errorize(fallbackException), cls=JSONEncoder)

        responseHeaders = []
        if responseBody is not None:
            # TODO Decide encoding
            encoding = "utf-8"
            responseBody = responseBody.encode(encoding)
            responseHeaders += [("Content-Type", f"application/json; charset={encoding}")]
        responseBodyLength = len(responseBody) if responseBody is not None else 0
        responseHeaders += [("Content-Length", f"{responseBodyLength}")]
        allow = "POST" if allowPost else ""
        responseHeaders += [("Allow", allow)]
        if len(acceptedEncoding) > 0:
            # TODO Compress
            pass

        startResponse(f"{statusCode} {statusMessage}", responseHeaders)

        return [responseBody]

    return application
