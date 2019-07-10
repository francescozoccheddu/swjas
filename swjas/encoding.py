import zlib
import brotli
import gzip
from datetime import datetime
import json
from . import exceptions


class JsonException(exceptions.PrintableException):
    pass


class JsonEncodeException(JsonException):
    pass


class JsonEncodeObjectException(JsonEncodeException):

    def __init__(self, obj, message=None):
        super().__init__(message=message)
        self._object = obj

    @property
    def object(self):
        return self._object


class JSONDecodeException(JsonException):

    def __init__(self, cause=None):
        message = f"{cause.msg} (line {cause.lineno}, column {cause.colno})" if cause is not None else None
        super().__init__(message=message)


class _JSONEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        try:
            if hasattr(obj, "_json"):
                return obj._json
            return json.JSONEncoder.default(self, obj)
        except Exception as e:
            raise JsonEncodeObjectException(obj) from e


def toJsonString(obj, indent=None, ensureAscii=True):
    try:
        return json.dumps(obj, cls=_JSONEncoder, indent=indent, ensure_ascii=ensureAscii)
    except JsonEncodeObjectException as e:
        raise e
    except Exception as e:
        raise JsonEncodeException() from e


def fromJsonString(js, allowEmpty=True):
    if allowEmpty and js == "" or js.isspace():
        return None
    try:
        return json.loads(js)
    except json.JSONDecodeError as e:
        raise JSONDecodeException(e)


class EncodingException(exceptions.PrintableException):
    pass


class StringEncodingException(EncodingException):
    pass


class UnknownCharsetException(StringEncodingException):

    def __init__(self, charset):
        super().__init__(message=f"Unknown charset '{charset}'")
        self._charset = charset

    @property
    def charset(self):
        return self._charset


def _stringEncoding(data, charset, decode):
    if not isinstance(charset, str):
        raise TypeError("Charset must be str")
    if decode:
        if not isinstance(data, bytes):
            raise TypeError("Data must be bytes")
    else:
        if not isinstance(data, str):
            raise TypeError("Data must be str")
    try:
        if decode:
            return data.decode(charset)
        else:
            return data.encode(charset)
    except LookupError:
        raise UnknownCharsetException(charset)
    except:
        raise StringEncodingException()


class DataEncodingException(EncodingException):
    pass


class UnknownEncodingTypeException(DataEncodingException):

    def __init__(self, encoding):
        super().__init__(message=f"Unknown encoding type '{encoding}'")
        self._encoding = encoding

    @property
    def encoding(self):
        return self._encoding


_dataEncoders = {
    "identity": lambda x: x,
    "gzip": gzip.compress,
    "deflate": zlib.compress,
    "br": brotli.compress
}

_dataDecoders = {
    "identity": lambda x: x,
    "gzip": gzip.decompress,
    "deflate": zlib.decompress,
    "br": brotli.decompress
}


def _dataEncoding(data, encoding, decode):
    if not isinstance(encoding, str):
        raise TypeError("Encoding type must be str")
    if not isinstance(data, bytes):
        raise TypeError("Data must be bytes")
    encoders = _dataDecoders if decode else _dataEncoders
    encoder = encoders.get(encoding.strip().lower(), None)
    if encoder is None:
        raise UnknownEncodingTypeException(encoding)
    try:
        return encoder(data)
    except:
        raise DataEncodingException()


def encodeData(data, encoding):
    return _dataEncoding(data, encoding, False)


def encodeString(data, charset):
    return _stringEncoding(data, charset, False)


def decodeData(data, encoding):
    return _dataEncoding(data, encoding, True)


def decodeString(data, charset):
    return _stringEncoding(data, charset, True)


def encode(data, charset="utf-8", encoding="identity"):
    data = encodeString(data, charset)
    return encodeData(data, encoding)


def decode(data, charset="utf-8", encoding="identity"):
    data = decodeData(data, encoding)
    return decodeString(data, charset)


class NoCharsetSupportedException(StringEncodingException):
    pass


class NoEncodingSupportedException(DataEncodingException):
    pass


def tryEncode(data, suppCharsets=["utf-8"], suppEncodings=["identity"]):
    ok = False
    for charset in suppCharsets:
        try:
            data = encodeString(data, charset)
        except StringEncodingException:
            continue
        else:
            ok = True
            break
    if not ok:
        raise NoCharsetSupportedException()
    ok = False
    for encoding in suppEncodings:
        try:
            data = encodeData(data, encoding)
        except DataEncodingException:
            continue
        else:
            ok = True
            break
    if not ok:
        raise NoEncodingSupportedException()
    return (data, charset, encoding)
