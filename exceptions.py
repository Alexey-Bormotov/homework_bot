class HTTPConnectionError(Exception):
    """Ошибка подключения к API."""
    pass


class JSONConvertError(Exception):
    """Ошибка преобразования ответа от API в JSON."""
    pass


class JSONContentError(Exception):
    """Ошибка в содержимом JSON'а."""
    pass


class ParsingError(Exception):
    """Ошибка при распознавании данных."""
    pass
