class HTTPConnectionException(Exception):
    """Ошибка подключения к API."""
    pass

class JSONConvertException(Exception):
    """Ошибка преобразования ответа от API в JSON."""
    pass

class JSONContentException(Exception):
    """Ошибка в содержимом JSON'а."""
    pass

class ParsingException(Exception):
    """Ошибка при распознавании данных."""
    pass
