from urllib import parse as urlparse
import json
from . import exceptions
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

    headerWeightedListRegex = re.compile('(?P<value>[^;]*)(;q=(?P<weight>.*))?')
    mimeRegex = re.compile('(?P<type>[^;]*)[^(;charset=)]*(;charset=(?P<charset>.*))?')

    def parseMime(header):
        header = header.strip()
        if header != "":
            match = mimeRegex.match(header)
            if match is not None:
                t, c = match.group("type"), match.group("charset")
                if c is not None:
                    if c.startswith("/"):
                        c = c[1:]
                    if c.endswith("/"):
                        c = c[:-1]
                return (t, c)
        return (None, None)

    def parseHeaderList(header):
        return list(filter(None, map(str.strip, header.split(","))))

    def parseHeaderWeightedListItem(item):
        match = headerWeightedListRegex.match(item.strip())
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

    def parseHeaderWeightedList(header):
        inList = parseHeaderList(header)
        outList = []
        for item in inList:
            item = parseHeaderWeightedListItem(item)
            if item is not None:
                outList += [item]
        outList.sort(key=lambda i: -i[1])
        return list(map(lambda i: i[0], outList))

    def application(environ, startResponse):

        allowPost = True

        # Capture path
        path = environ.get("PATH_INFO", "")
        if path.startswith("/") or path.startswith("\\"):
            path = path[1:]
        if path.endswith("/") or path.endswith("\\"):
            path = path[:-1]

        # Warn if JSON not accepted
        acceptedMimes = parseHeaderList(environ.get("HTTP_ACCEPT", ""))
        if len(acceptedMimes) > 0 and not any(mime in acceptedMimes for mime in ["*/*", "application/*", "application/json"]):
            _logger.info(f"Request to path '{path}' does not accept JSON reponse type: ignoring this fact")

        # Catch HTTP exceptions
        try:
            # Ensure POST method
            method = environ.get("REQUEST_METHOD")
            if method != "POST":
                _logger.info(f"Rejected request to '{path}' with method '{method}'")
                raise exceptions.HttpException.build(405)

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
                requestBodyTypeHeader = environ.get("CONTENT_TYPE", "").lower()
                requestBodyType, requestBodyCharset = parseMime(requestBodyTypeHeader)

                if requestBodyCharset is None:
                    requestBodyCharset = "utf-8"

                if requestBodyType is not None and requestBodyType != "application/json":
                    _logger.info(f"Rejected request to '{path}' with non-JSON body type")
                    raise exceptions.HttpException.build(415, message="Expected JSON content type")

                requestBody = bytearray(requestBody)

                requestBodyEncoding = environ.get("HTTP_CONTENT_ENCODING", "").strip()
                if requestBodyEncoding == "":
                    requestBodyEncoding = "identity"

                try:
                    if requestBodyEncoding == "identity":
                        pass
                    elif requestBodyEncoding == "gzip":
                        import gzip
                        requestBody = gzip.decompress(requestBody)
                    elif requestBodyEncoding == "deflate":
                        import zlib
                        requestBody = zlib.decompress(requestBody)
                    elif requestBodyEncoding == "br":
                        import brotli
                        requestBody = brotli.decompress(requestBody)
                    else:
                        _logger.info(f"Rejected request to '{path}' with unsupported encoding type '{encoding}'")
                        raise exceptions.HttpException.build(415, message="Unsupported content encoding type")
                    requestBody = requestBody.decode(requestBodyCharset)
                except exceptions.HttpException as e:
                    raise e
                except:
                    _logger.info(f"Rejected request to '{path}' with undecodable body")
                    raise exceptions.BadRequestException("Unable to decode content")

                if requestBody == "" or requestBody.isspace():
                    jsonRequestBody = None
                else:
                    try:
                        jsonRequestBody = json.loads(requestBody)
                    except json.JSONDecodeError as e:
                        _logger.info(f"Rejected request to '{path}' with invalid JSON body")
                        raise exceptions.BadRequestException() from exceptions.JSONDecodeException(e)

                # Call handler
                try:
                    jsonResponseBody = handler(jsonRequestBody)
                    if jsonResponseBody is None:
                        responseBody = None
                    else:
                        try:
                            responseBody = json.dumps(jsonResponseBody, cls=JSONEncoder)
                        except:
                            _logger.exception("Error while encoding JSON response body")
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

        # Choose charset
        acceptedCharsets = parseHeaderWeightedList(environ.get("HTTP_ACCEPT_CHARSET", "")) + ["utf-8"]
        if responseBody is not None:
            for charset in acceptedCharsets:
                try:
                    responseBody = responseBody.encode(charset)
                except:
                    _logger.warning(f"Error while trying to encode response body with charset '{charset}'")
                else:
                    responseHeaders += [("Content-Type", f"application/json; charset={charset}")]
                    break

            # Choose encoding type
            acceptedEncoding = parseHeaderWeightedList(environ.get("HTTP_ACCEPT_ENCODING", "")) + ["identity"]
            for encoding in acceptedEncoding:
                try:
                    if encoding == "identity":
                        pass
                    elif encoding == "gzip":
                        import gzip
                        responseBody = gzip.compress(responseBody)
                    elif encoding == "deflate":
                        import zlib
                        responseBody = zlib.compress(responseBody)
                    elif encoding == "br":
                        import brotli
                        responseBody = brotli.compress(responseBody)
                    else:
                        _logger.info(f"Skipping unsupported accepted encoding type '{encoding}'")
                        continue
                except:
                    _logger.warning(f"Error while trying to encode response body with encoding type '{encoding}'")
                else:
                    responseHeaders += [("Content-Encoding", f"{encoding}")]
                    break

        # Calculate content length
        responseBodyLength = len(responseBody) if responseBody is not None else 0
        responseHeaders += [("Content-Length", f"{responseBodyLength}")]

        # Provide allowed methods
        allow = "POST" if allowPost else ""
        responseHeaders += [("Allow", allow)]

        # Start response
        startResponse(f"{statusCode} {statusMessage}", responseHeaders)
        return [responseBody]

    return application
