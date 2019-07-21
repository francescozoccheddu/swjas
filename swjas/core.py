from urllib import parse as urlparse
from . import exceptions
from . import encoding
import logging
from datetime import datetime
import re

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


_headerWeightedListRegex = re.compile('(?P<value>[^;]*)(;q=(?P<weight>.*))?')
_mimeRegex = re.compile('(?P<type>[^;]*)[^(;charset=)]*(;charset=(?P<charset>.*))?')


def _parseMime(header):
    header = header.strip().lower()
    if header != "":
        match = _mimeRegex.match(header)
        if match is not None:
            t, c = match.group("type"), match.group("charset")
            if c is not None:
                if c.startswith("/"):
                    c = c[1:]
                if c.endswith("/"):
                    c = c[:-1]
            return (t, c)
    return (None, None)


def _parseHeaderList(header):
    return list(filter(None, map(str.strip, header.split(","))))


def _parseHeaderWeightedListItem(item):
    match = _headerWeightedListRegex.match(item.strip())
    if match is not None:
        v, w = match.group("value"), match.group("weight")
        if w is not None:
            try:
                w = float(w.strip())
            except ValueError:
                pass
            else:
                return (v, w)
        else:
            return (v, 1)
    return (None, None)


def _parseHeaderWeightedList(header, overrideWeight=None):
    if overrideWeight is None:
        overrideWeight = (lambda _, w: w)
    inList = _parseHeaderList(header)
    outList = []
    for item in inList:
        value, weight = _parseHeaderWeightedListItem(item)
        if value is not None:
            weight = overrideWeight(value, weight)
            outList += [(value, weight)]
    outList.sort(key=lambda i: -i[1])
    return list(map(lambda i: i[0], outList))


def makeApplication(routes, allowEmptyRequestBody=True):
    # TODO Add docs
    # Prepare route dict
    routeDict = {}
    for path, handler in map(_cleanRoute, routes):
        routeDict[path] = handler

    def application(environ, startResponse):

        allowPost = True

        # Capture path
        path = environ.get("PATH_INFO", "")
        if path.startswith("/") or path.startswith("\\"):
            path = path[1:]
        if path.endswith("/") or path.endswith("\\"):
            path = path[:-1]

        # Warn if JSON not accepted
        acceptedMimes = _parseHeaderList(environ.get("HTTP_ACCEPT", "").lower())
        if not any(mime in acceptedMimes for mime in ["*/*", "application/*", "application/json"]):
            _logger.info(f"Request to path '{path}' does not accept JSON reponse type: serving JSON anyway")

        # Catch HTTP exceptions
        try:
            # Ensure POST method
            method = environ.get("REQUEST_METHOD")
            if method != "POST":
                _logger.info(f"Rejected request to '{path}' with method '{method}'")
                raise exceptions.HttpException.build(405, message="Expected POST method", requestedMethod=method)

            # Ensure no query
            query = environ.get("QUERY_STRING", "").strip()
            if query != "":
                allowPost = False
                _logger.info(f"Rejected request to '{path}' with query '{query}'")
                raise exceptions.BadRequestException(message="Unexpected query")

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
                requestBodyType, requestBodyCharset = _parseMime(environ.get("CONTENT_TYPE", ""))

                if requestBodyCharset is None:
                    _logger.info(f"Request to path '{path}' does not specify content charset: assuming utf-8")
                    requestBodyCharset = "utf-8"

                if requestBodyType is None:
                    _logger.info(f"Request to path '{path}' does not specify content type: assuming JSON")
                elif requestBodyType != "application/json":
                    _logger.info(f"Rejected request to '{path}' with non-JSON body type")
                    raise exceptions.HttpException.build(415, message="Expected JSON content type", requestContentType=requestBodyType)

                requestBodyEncoding = environ.get("HTTP_CONTENT_ENCODING", "")
                if requestBodyEncoding == "":
                    requestBodyEncoding = "identity"

                try:
                    requestBody = encoding.decode(requestBody, requestBodyCharset, requestBodyEncoding)
                except encoding.EncodingException as e:
                    _logger.info(f"Rejected request to '{path}' with undecodable body")
                    raise exceptions.BadRequestException(message="Unable to decode request body") from e

                try:
                    jsonRequestBody = encoding.fromJsonString(requestBody, allowEmpty=allowEmptyRequestBody)
                except encoding.JsonException as e:
                    _logger.info(f"Rejected request to '{path}' with invalid JSON body")
                    raise exceptions.BadRequestException(message="Error while decoding request JSON body") from e

                # Call handler
                try:
                    jsonResponseBody = handler(jsonRequestBody)
                    try:
                        responseBody = encoding.toJsonString(jsonResponseBody)
                    except:
                        _logger.error("Error while encoding JSON response body")
                        raise
                except exceptions.HttpException as e:
                    raise e
                except Exception as e:
                    _logger.exception(f"Exception while processing request to '{path}'")
                    raise exceptions.ServerErrorException(message="Error while processing the request")
                else:
                    statusCode = 200
                    statusMessage = "OK"

            else:
                # No handler found
                allowPost = False
                _logger.info(f"Rejected request to unrouted path '{path}'")
                raise exceptions.NotFoundException(message="Invalid path", path=path)

        except exceptions.HttpException as e:
            # Prepare HTTP exception response
            def errorize(json):
                return {"error": json}

            try:
                statusCode = e.statusCode
                statusMessage = e.statusMessage
                responseBody = encoding.toJsonString(errorize(e))
            except encoding.JsonException:
                _logger.exception("Error while preparing JSON response for HttpException")
                fallbackException = exceptions.ServerErrorException(message="Error while collecting information about a previous error")
                statusCode = fallbackException.statusCode
                statusMessage = fallbackException.message
                responseBody = encoding.toJsonString(errorize(fallbackException))

        responseHeaders = []

        # Encode
        def overrideCharsetWeight(c, w): return 2 if c.lower() == "utf-8" else w
        acceptedCharsets = _parseHeaderWeightedList(environ.get("HTTP_ACCEPT_CHARSET", ""), overrideCharsetWeight)
        acceptedEncodingTypes = _parseHeaderWeightedList(environ.get("HTTP_ACCEPT_ENCODING", "")) + ["identity"]

        responseBody, chosenCharset, chosenEncoding = encoding.tryEncode(responseBody, acceptedCharsets + ["utf-8"], acceptedEncodingTypes)

        if not chosenCharset in acceptedCharsets:
            _logger.info(f"No accepted charset found for request to path '{path}': serving utf-8 anyway")

        responseHeaders += [("Content-Type", f"application/json;charset={chosenCharset}")]
        responseHeaders += [("Content-Encoding", chosenEncoding)]

        # Calculate content length
        responseBodyLength = len(responseBody) if responseBody is not None else 0
        responseHeaders += [("Content-Length", f"{responseBodyLength}")]

        # Provide allowed methods
        allow = "POST" if allowPost else ""
        responseHeaders += [("Allow", allow)]

        # CORS
        responseHeaders += [("Access-Control-Allow-Origin", "*")]

        # Start response
        startResponse(f"{statusCode} {statusMessage}", responseHeaders)
        return [responseBody]

    return application
