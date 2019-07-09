from . import exceptions


class _RequestErrorException(Exception):

    def __init__(self, data, statusCode):
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

    def __str__(self):
        txt = f"Request failed: {self._statusCode} {self.statusMessage}"
        if self._data is not None:
            txt += f"\n{self._data}"
        return txt


def service(service, host, data=None, timeout=15):
    if not isinstance(service, str):
        raise TypeError("Service must be string")
    if not isinstance(host, str):
        raise TypeError("Host must be string")
    if not isinstance(timeout, (int, float)):
        raise TypeError("Timeout must be int or float")

    from urllib import parse
    host = parse.urlparse(host)

    if (not all([host.netloc])) or any([host.path, host.query, host.params, host.fragment]):
        raise ValueError("Invalid host")
    if host.scheme:
        if host.scheme != "http":
            raise ValueError("Expected http scheme")
    else:
        host = host._replace(scheme="http")

    service = parse.urlparse(service)
    if (not all([service.path])) or any([service.scheme, service.query, service.params, service.fragment]):
        raise ValueError("Invalid service")

    url = parse.urljoin(host.geturl(), service.geturl())

    return request(url, data, timeout)


def request(url, data=None, timeout=15):
    if not isinstance(url, str):
        raise TypeError("Url must be string")
    if not isinstance(timeout, (int, float)):
        raise TypeError("Timeout must be int or float")
    if timeout <= 0:
        raise ValueError("Timeout must be positive")

    import requests
    res = requests.post(url, json=data, timeout=timeout)

    if not res.status_code.ok:
        raise _RequestErrorException(res.json(), res.status_code)

    return res.json()


def _main():

    import argparse

    def makeArgparseRangeType(min, max, integer):
        import argparse

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
        import argparse
        import os
        path = os.path.abspath(arg)
        if not os.path.exists(path):
            raise argparse.ArgumentTypeError(f"file '{path}' does not exist")
        return arg

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("url", metavar="URL", help="Request URL")
    parser.add_argument("-if", "--inputfile", metavar="INPUT_FILE", default=None, help="Use an input file instead of stdin", type=argparseFileType)
    parser.add_argument("-to", "--timeout", default=15, metavar="TIMEOUT", help="Request timeout seconds", type=makeArgparseRangeType(1, 60, False))
    parser.add_argument("--indent", default=4, metavar="SPACES", help="Indentation tab size (-1 to minify)", type=makeArgparseRangeType(-1, 10, True))
    parser.add_argument("--outputstatus", action="store_true", help="Output a JSON object containing status info and response")
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
        else:
            rawInput = sys.stdin.read()

        import json

        try:
            jsonInput = json.loads(rawInput)
        except json.JSONDecodeError as e:
            logger.exception("Error while parsing input:\n%s (line %s, column %s)", e.msg, e.lineno, e.colno)
            sys.exit(1)

        def printResult(statusCode, data):
            from .core import JSONEncoder
            if args.outputstatus:
                out = {
                    "statusCode": statusCode,
                    "statusMessage": exceptions.getStatusMessage(statusCode),
                    "data": data
                }
            else:
                out = data
                if exceptions.isOKStatus(statusCode):
                    logger.error("Bad HTTP response (%s %s)", statusCode, exceptions.getStatusMessage(statusCode))
            indent = args.indent if args.indent > 0 else None
            print(json.dumps(out, indent=indent, cls=JSONEncoder))

        try:
            rawResult = request(args.url, jsonInput, args.timeout)
            printResult(200, rawResult)
        except _RequestErrorException as e:
            printResult(e.statusCode, e.data)
            sys.exit(2)
        except Exception:
            logger.exception("Error while performing request")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")


if __name__ == "__main__":
    _main()
