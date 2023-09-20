import requests
from flask import flash


def get_response(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException:
        flash('Произошла ошибка при проверке', 'danger')
