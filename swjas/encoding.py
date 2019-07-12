import zlib
import brotli
import gzip
from datetime import datetime
import json
from . import exceptions


class JsonException(exceptions.PrintableException):
    pass


class JsonEncodeException(JsonException):

    def __init__(self, obj, **kwargs):
        super().__init__(**kwargs)
        self._object = obj

    @property
    def object(self):
        return self._object


class JSONDecodeException(JsonException):

    def __init__(self, source, cause=None, **kwargs):
        self._source = source
        if cause is None:
            super().__init__()
        else:
            if not isinstance(cause, json.JSONDecodeError):
                raise TypeError("Cause must be json.JSONDecodeError")
            super().__init__(message=cause.msg, line=cause.lineno, column=cause.colno)

    @property
    def source(self):
        return self._source


strfyUnknownObjectTypes = False


class _JSONEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, type):
            return obj.__name__
        try:
            if hasattr(obj, "_json"):
                return obj._json
        except Exception as e:
            raise JsonEncodeException(obj) from e
        try:
            return json.JSONEncoder.default(self, obj)
        except TypeError as e:
            if strfyUnknownObjectTypes:
                return str(obj)
            else:
                raise JsonEncodeException(obj) from e


def toJsonString(obj, indent=None, ensureAscii=True):
    return json.dumps(obj, cls=_JSONEncoder, indent=indent, ensure_ascii=ensureAscii)


def fromJsonString(js, allowEmpty=True):
    if allowEmpty and js == "" or js.isspace():
        return None
    try:
        return json.loads(js)
    except json.JSONDecodeError as e:
        raise JSONDecodeException(js, e)


class EncodingException(exceptions.PrintableException):
    pass


class StringEncodingException(EncodingException):
    pass


class UnknownCharsetException(StringEncodingException):

    def __init__(self, charset, **kwargs):
        if not isinstance(charset, str):
            raise TypeError("Charset must be str")
        super().__init__(charset=charset, message=f"Unknown charset '{charset}'", **kwargs)


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
        raise StringEncodingException(charset=charset, message=f"Error while {'de' if decode else 'en'}coding string")


class DataEncodingException(EncodingException):
    pass


class UnknownEncodingTypeException(DataEncodingException):

    def __init__(self, encoding, **kwargs):
        if not isinstance(encoding, str):
            raise TypeError("Encoding must be str")
        super().__init__(encoding=encoding, message=f"Unknown encoding type '{encoding}'", **kwargs)


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
        raise DataEncodingException(encoding=encoding, message=f"Error while {'de' if decode else 'en'}coding data'")


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
