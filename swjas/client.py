from . import exceptions
from . import encoding as swjasEncoding
import requests
from urllib import parse


class RequestException(exceptions.PrintableException):

    def __init__(self, requestBody, **kwargs):
        super().__init__(**kwargs)
        self._requestBody = requestBody

    @property
    def requestBody(self):
        return self._requestBody


class HttpException(RequestException):

    def __init__(self, requestBody, responseBody, statusCode, **kwargs):
        if not isinstance(statusCode, int):
            raise TypeError("Status code must be int")
        super().__init__(requestBody, statusCode=statusCode, statusMessage=exceptions.getStatusMessage(statusCode), **kwargs)
        self._responseBody = responseBody

    @property
    def responseBody(self):
        return self._responseBody


class TimeoutException(RequestException):

    def __init__(self, requestBody, timeout, **kwargs):
        super().__init__(requestBody, timeout=timeout, **kwargs)


class ConnectionException(RequestException):
    pass


class JSONDecodeException(RequestException):
    pass


class URLException(exceptions.PrintableException):

    def __init__(self, url, message, **kwargs):
        super().__init__(url=url, message=message, **kwargs)


def validateUrl(url):
    if not isinstance(url, str):
        raise TypeError("Expected str")
    url = parse.urlparse(url)
    if not url.netloc:
        raise URLException(url, "URL has no netloc")
    if any([url.query, url.params, url.fragment]):
        raise URLException(url, "URL cannot include parameters, query or fragment")
    if url.scheme:
        if url.scheme != "http":
            raise URLException(url, "Expected http scheme")
    else:
        url = url._replace(scheme="http")
    return url.geturl()


def validateHost(host):
    if not isinstance(host, str):
        raise TypeError("Expected str")
    host = parse.urlparse(host)
    if not host.netloc:
        raise URLException(host, "Host has no netloc")
    if any([host.path, host.query, host.params, host.fragment]):
        raise URLException(host, "Host cannot include path, parameters, query or fragment")
    if host.scheme and host.scheme != "http":
        raise URLException(host, "Expected http scheme")
    return f"//{host.netloc}"


def validateService(service):
    if not isinstance(service, str):
        raise TypeError("Expected str")
    service = parse.urlparse(service)
    if not service.path:
        raise URLException(service, "Service has no path")
    if any([service.netloc, service.scheme, service.query, service.params, service.fragment]):
        raise URLException(service, "Service cannot include scheme, netloc, parameters, query or fragment")
    return service.path


def service(host, service, **kwargs):
    # TODO Add docs

    host = validateHost(host)
    service = validateService(service)

    url = parse.urljoin(host, service)

    return request(url, **kwargs)


def request(url, body=None, timeout=15, encoding="identity"):
    # TODO Add docs

    if not isinstance(url, str):
        raise TypeError("Url must be string")
    if not isinstance(timeout, (int, float)):
        raise TypeError("Timeout must be int or float")
    if timeout <= 0:
        raise ValueError("Timeout must be positive")

    url = validateUrl(url)

    body = swjasEncoding.toJsonString(body)
    body = swjasEncoding.encode(body, encoding=encoding)

    headers = {
        "Content-Type": "application/json;charset=utf-8",
        "Content-Encoding": encoding,
        "Accept-Charset": "utf-8",
        "Accept": "application/json"
    }

    try:
        res = requests.post(url, data=body, timeout=timeout, allow_redirects=False, headers=headers)
        if not res.ok:
            res.raise_for_status()
    except requests.HTTPError as e:
        try:
            resBody = swjasEncoding.fromJsonString(res.text)
        except swjasEncoding.JSONDecodeException:
            resBody = None
        raise HttpException(body, resBody, e.response.status_code) from None
    except requests.Timeout:
        raise TimeoutException(body, timeout) from None
    except requests.ConnectionError:
        raise ConnectionException(body) from None
    except requests.RequestException:
        raise RequestException(body) from None
    try:
        return swjasEncoding.fromJsonString(res.text, False)
    except swjasEncoding.JSONDecodeException as e:
        raise JSONDecodeException(body) from e


def _main():

    import argparse

    def makeArgparseRangeType(min, max, integer):

        def validate(arg):
            try:
                value = int(arg) if integer else float(arg)
            except ValueError:
                raise argparse.ArgumentTypeError(f"expected {'int' if integer else 'float'}")
            if not min <= value <= max:
                raise argparse.ArgumentTypeError(f"value not in range [{min},{max}]")
            return value

        return validate

    def argparseFileType(arg):
        import os
        path = os.path.abspath(arg)
        if not os.path.exists(path):
            raise argparse.ArgumentTypeError(f"file '{path}' does not exist")
        return arg

    def argparseUrlType(arg):
        try:
            return validateUrl(arg)
        except URLException as e:
            raise argparse.ArgumentTypeError(e.message)

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("url", metavar="URL", help="Request URL", type=argparseUrlType)
    parser.add_argument("-if", "--inputfile", metavar="INPUT_FILE", default=None, help="Use an input file instead of stdin", type=argparseFileType)
    parser.add_argument("-to", "--timeout", default=15, metavar="TIMEOUT", help="Request timeout seconds", type=makeArgparseRangeType(1, 60, False))
    parser.add_argument("--indent", default=4, metavar="SPACES", help="Indentation tab size (-1 to minify)", type=makeArgparseRangeType(-1, 10, True))
    parser.add_argument("--outputstatus", action="store_true", help="Output a JSON object containing status info and response")
    parser.add_argument("--encoding", default="identity", metavar="ENCODING", choices=swjasEncoding._dataEncoders.keys(), help="Request encoding type")
    args = parser.parse_args()

    try:

        import sys
        import logging
        logger = logging.getLogger("swjas.client")

        if args.inputfile is not None:
            try:
                with open(args.inputfile, "r") as inputFile:
                    rawInput = inputFile.read()
            except IOError as e:
                logger.error("Error while reading from input file:\n%s", e.strerror)
                sys.exit(1)
            except UnicodeDecodeError as e:
                logger.error("Error while decoding input file text")
                sys.exit(1)
        else:
            rawInput = sys.stdin.read()

        jsonInput = swjasEncoding.fromJsonString(rawInput)

        def output(out):
            indent = args.indent if args.indent > 0 else None
            print(swjasEncoding.toJsonString(out, indent=indent))

        def outputResult(status, response):
            output({
                "statusCode": status,
                "statusMessage": exceptions.getStatusMessage(status),
                "data": response
            })
        
        def outputError(exception):
            output({
                "error": exception
            })

        try:
            responseBody = request(args.url, jsonInput, args.timeout, args.encoding)
        except HttpException as e:
            if args.outputstatus:
                outputResult(e.statusCode, e.responseBody)
            else:
                logger.error(e)
        except RequestException as e:
            if args.outputstatus:
                outputError(e)
            else:
                logger.error(e)
        else:
            outputResult(200, responseBody)

    except KeyboardInterrupt:
        logger.error("Interrupted by user")


if __name__ == "__main__":
    _main()
