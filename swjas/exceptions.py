

def getStatusMessage(statusCode, default="Unknown status"):
    # TODO Add docs
    return {
        100: 'Continue',
        101: 'Switching Protocols',
        102: 'Processing',
        200: 'OK',
        201: 'Created',
        202: 'Accepted',
        203: 'Non-authoritative Information',
        204: 'No Content',
        205: 'Reset Content',
        206: 'Partial Content',
        207: 'Multi-Status',
        208: 'Already Reported',
        226: 'IM Used',
        300: 'Multiple Choices',
        301: 'Moved Permanently',
        302: 'Found',
        303: 'See Other',
        304: 'Not Modified',
        305: 'Use Proxy',
        307: 'Temporary Redirect',
        308: 'Permanent Redirect',
        400: 'Bad Request',
        401: 'Unauthorized',
        402: 'Payment Required',
        403: 'Forbidden',
        404: 'Not Found',
        405: 'Method Not Allowed',
        406: 'Not Acceptable',
        407: 'Proxy Authentication Required',
        408: 'Request Timeout',
        409: 'Conflict',
        410: 'Gone',
        411: 'Length Required',
        412: 'Precondition Failed',
        413: 'Payload Too Large',
        414: 'Request-URI Too Long',
        415: 'Unsupported Media Type',
        416: 'Requested Range Not Satisfiable',
        417: 'Expectation Failed',
        418: "I'm a teapot",
        421: 'Misdirected Request',
        422: 'Unprocessable Entity',
        423: 'Locked',
        424: 'Failed Dependency',
        426: 'Upgrade Required',
        428: 'Precondition Required',
        429: 'Too Many Requests',
        431: 'Request Header Fields Too Large',
        444: 'Connection Closed Without Response',
        451: 'Unavailable For Legal Reasons',
        499: 'Client Closed Request',
        500: 'Internal Server Error',
        501: 'Not Implemented',
        502: 'Bad Gateway',
        503: 'Service Unavailable',
        504: 'Gateway Timeout',
        505: 'HTTP Version Not Supported',
        506: 'Variant Also Negotiates',
        507: 'Insufficient Storage',
        508: 'Loop Detected',
        510: 'Not Extended',
        511: 'Network Authentication Required',
        599: 'Network Connect Timeout Error'
    }.get(statusCode, default)


def isOKStatus(statusCode):
    # TODO Add docs
    return 200 <= statusCode < 300


class PrintableException(Exception):
    # TODO Add docs

    def __init__(self, message=None):
        # TODO Add docs
        super().__init__()
        self._message = str(message) if message is not None else None

    @property
    def message(self):
        return self._message

    @property
    def _json(self):
        json = {
            "type": self.__class__.__name__
        }
        if isinstance(self.__cause__, PrintableException):
            json["cause"] = self.__cause__._json
        if self._message is not None:
            json["message"] = self._message
        return json

    @property
    def shortDescription(self):
        # TODO Add docs
        desc = self.__class__.__name__
        if self._message is not None:
            desc += f": {self._message}"
        return desc

    def __str__(self):
        txt = self.shortDescription
        if isinstance(self.__cause__, PrintableException):
            txt += f"\nCaused by:\n{self.__cause__}"
        return txt

    def __repr__(self):
        return repr(self._json)


class HttpException(PrintableException):
    # TODO Add docs

    @staticmethod
    def build(statusCode, statusMessage=None, message=None):
        # TODO Add docs
        fields = {"statusCode": statusCode}
        if statusMessage != None:
            fields["statusMessage"] = statusMessage
        return type("HttpException", (HttpException,), fields)(message)

    @property
    def statusCode(self):
        raise NotImplementedError

    @property
    def statusMessage(self):
        return getStatusMessage(self.statusCode)

    @property
    def shortDescription(self):
        return f"{super().shortDescription} ({self.statusCode} {self.statusMessage})"

    @property
    def _json(self):
        json = super()._json
        json["statusCode"] = self.statusCode
        json["statusMessage"] = self.statusMessage
        return json


class AuthorizationException(HttpException):
    statusCode = 401


class BadRequestException(HttpException):
    statusCode = 400


class ForbiddenException(HttpException):
    statusCode = 403


class NotFoundException(HttpException):
    statusCode = 404


class ServerErrorException(HttpException):
    statusCode = 500


class ServiceUnavailableException(HttpException):
    statusCode = 503


class NotImplementedException(HttpException):
    statusCode = 501


