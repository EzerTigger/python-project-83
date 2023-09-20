import validators
from urllib.parse import urlparse


def normalize_url(url):
    o = urlparse(url)
    scheme = o.scheme
    name = o.netloc
    return f'{scheme}://{name}'


def validate(start_url):
    errors = []
    if len(start_url) > 255:
        errors.append('URL превышает 255 символов')
    if not validators.url(start_url):
        errors.append('Некорректный URL')
    if not start_url:
        errors.append('URL обязателен')
    return errors
