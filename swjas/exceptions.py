

def getStatusMessage(statusCode, default="Unknown status"):
    # TODO Add docs
    if not isinstance(statusCode, int):
        raise TypeError("Status code must be int")
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
    if not isinstance(statusCode, int):
        raise TypeError("Status code must be int")
    return 200 <= statusCode < 300


class PrintableException(Exception):
    # TODO Add docs

    def __init__(self, **kwargs):
        # TODO Add docs
        super().__init__(kwargs)

    @property
    def _json(self):
        json = {
            "type": self.__class__,
        }
        if isinstance(self.__cause__, PrintableException):
            json["cause"] = self.__cause__
        json = {**json, **self.dict}
        return json

    def __getitem__(self, name):
        return self.dict[name]

    def __getattr__(self, name):
        try:
            return super().__getattr__(name)
        except AttributeError as e:
            try:
                return self[name]
            except KeyError:
                raise e from None

    @staticmethod
    def naifDictDescription(dict):
        # TODO Add docs
        desc = ""
        for key, value in dict.items():
            if desc != "":
                desc += ", "
            if isinstance(value, str):
                value = f"'{value}'"
            desc += f"{key}={value}"
        return desc

    @property
    def dict(self):
        return self.args[0]

    def __str__(self):
        desc = PrintableException.naifDictDescription(self.dict)
        txt = self.__class__.__name__
        if desc != "":
            txt += ": "
        txt += desc
        return txt

    def __repr__(self):
        return f"{self.__class__.__name__}(**{repr(self.dict)})"


class HttpException(PrintableException):
    # TODO Add docs
    
    statusMessage = None

    @staticmethod
    def build(statusCode, statusMessage=None, **kwargs):
        # TODO Add docs
        fields = {"statusCode": statusCode}
        if statusMessage is not None:
            fields["statusMessage"] = statusMessage
        return type("HttpException", (HttpException,), fields)(**kwargs)

    def __init__(self, **kwargs):
        if not isinstance(self.statusCode, int):
            raise TypeError("Status code must be int")
        if self.statusMessage is None:
            self.statusMessage = getStatusMessage(self.statusCode)
        elif not isinstance(self.statusMessage, str):
            raise TypeError("Status message must be str or None")
        super().__init__(statusCode=self.statusCode, statusMessage=self.statusMessage, **kwargs)


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
