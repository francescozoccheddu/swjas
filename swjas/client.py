from . import exceptions
from . import encoding as swjasEncoding
import requests
from urllib import parse


class RequestException(exceptions.PrintableException):

    def __init__(self):
        super().__init__()


class HttpException(RequestException):

    def __init__(self, statusCode, data):
        super().__init__()
        self._data = data
        self._statusCode = statusCode

    @property
    def data(self):
        return self._data

    @property
    def statusCode(self):
        return self._statusCode

    @property
    def statusMessage(self):
        return exceptions.getStatusMessage(self._statusCode)

    @property
    def shortDescription(self):
        return f"{super().shortDescription} ({self.statusCode} {self.statusMessage})"

    @property
    def _json(self):
        json = super()._json
        json["statusCode"] = self.statusCode
        json["statusMessage"] = self.statusMessage
        if self._data is not None:
            json["data"] = self._data
        return json


class TimeoutException(RequestException):
    pass


class ConnectionException(RequestException):
    pass


class JSONDecodeException(RequestException):
    pass


class URLException(exceptions.PrintableException):
    pass


def validateUrl(url):
    url = parse.urlparse(url)
    if not url.netloc:
        raise URLException("URL has no netloc")
    if any([url.query, url.params, url.fragment]):
        raise URLException("URL cannot include parameters, query or fragment")
    if url.scheme:
        if url.scheme != "http":
            raise URLException("Expected http scheme")
    else:
        url = url._replace(scheme="http")
    return url.geturl()


def validateHost(host):
    host = parse.urlparse(host)
    if not host.netloc:
        raise URLException("Host has no netloc")
    if any([host.path, host.query, host.params, host.fragment]):
        raise URLException("Host cannot include path, parameters, query or fragment")
    if host.scheme and host.scheme != "http":
        raise URLException("Expected http scheme")
    return host.netloc


def validateService(service):
    service = parse.urlparse(service)
    if not service.path:
        raise URLException("Service has no path")
    if any([service.netloc, service.scheme, service.query, service.params, service.fragment]):
        raise URLException("Service cannot include scheme, netloc, parameters, query or fragment")
    return service.path


def service(host, service, data=None, timeout=15, encoding="identity"):
    # TODO Add docs

    host = validateHost(host)
    service = validateService(service)

    url = parse.urljoin(host.geturl(), service.geturl())

    return request(url, data, timeout)


def request(url, data=None, timeout=15, encoding="identity"):
    # TODO Add docs

    if not isinstance(url, str):
        raise TypeError("Url must be string")
    if not isinstance(timeout, (int, float)):
        raise TypeError("Timeout must be int or float")
    if timeout <= 0:
        raise ValueError("Timeout must be positive")

    url = validateUrl(url)

    data = swjasEncoding.toJsonString(data)
    data = swjasEncoding.encode(data, encoding=encoding)

    headers = {
        "Content-Type": "application/json;charset=utf-8",
        "Content-Encoding": encoding,
        "Accept-Charset": "utf-8",
        "Accept": "application/json"
    }

    try:
        res = requests.post(url, data=data, timeout=timeout, allow_redirects=False, headers=headers)
        if not res.ok:
            res.raise_for_status()
    except requests.HTTPError as e:
        try:
            data = e.response.json()
        except ValueError:
            data = None
        raise HttpException(e.response.status_code, data)
    except requests.Timeout:
        raise TimeoutException()
    except requests.ConnectionError:
        raise ConnectionException()
    except requests.RequestException:
        raise RequestException()

    if res.text == "" or res.text.isspace():
        return None
    else:
        try:
            return res.json()
        except ValueError:
            raise JSONDecodeException()


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

        import json

        try:
            jsonInput = json.loads(rawInput)
        except json.JSONDecodeError as e:
            logger.error("Error while parsing input:\n%s (line %s, column %s)", e.msg, e.lineno, e.colno)
            sys.exit(1)

        def printResult(statusCode, data):
            if args.outputstatus:
                out = {
                    "statusCode": statusCode,
                    "statusMessage": exceptions.getStatusMessage(statusCode),
                    "data": data
                }
            else:
                out = data
                if not exceptions.isOKStatus(statusCode):
                    logger.error("Bad HTTP response (%s %s)", statusCode, exceptions.getStatusMessage(statusCode))
            indent = args.indent if args.indent > 0 else None
            print(json.dumps(out, indent=indent))

        try:
            data = request(args.url, jsonInput, args.timeout, args.encoding)
        except HttpException as e:
            printResult(e.statusCode, e.data)
            sys.exit(2)
        except RequestException as e:
            logger.error("%s", e)
            sys.exit(1)
        else:
            printResult(200, data)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")


if __name__ == "__main__":
    _main()
