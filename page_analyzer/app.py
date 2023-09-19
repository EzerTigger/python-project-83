from flask import Flask, render_template, request, flash
from flask import redirect, url_for, abort
import psycopg2
import os
import datetime
import validators
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from psycopg2.extras import NamedTupleCursor


load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
app.config['DATABASE_URL'] = os.getenv('DATABASE_URL')


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


def connect_db():
    conn = psycopg2.connect(app.config['DATABASE_URL'])
    return conn


def page_parser(content):
    soup = BeautifulSoup(content, 'html.parser')
    title: str = soup.find('title').text if soup.find('title') else ''
    h1: str = soup.find('h1').text if soup.find('h1') else ''
    description: str = ''
    description_meta = soup.find('meta', attrs={'name': 'description'})

    if description_meta:
        description = description_meta['content']

    return {
        'title': title,
        'h1': h1,
        'description': description
    }


@app.route('/')
def index():
    return render_template(
        'index.html'
    )


@app.post('/urls')
def urls_post():
    url = request.form.to_dict().get('url')
    errors = validate(url)
    if errors:
        for error in errors:
            flash(error, 'danger')
        return render_template(
            'index.html',
            url_name=url
        ), 422

    url = normalize_url(url)

    conn = connect_db()
    with conn.cursor(cursor_factory=NamedTupleCursor) as cursor:

        cursor.execute(
            "SELECT * from urls where name=(%s)", (url,)
        )
        fetched_data = cursor.fetchone()
        if fetched_data:
            url_id: int = fetched_data.id
            flash('Страница уже существует', 'info')

        else:
            cursor.execute(
                "INSERT INTO urls "
                "(name, created_at) "
                "VALUES (%s, %s) RETURNING id;",
                (url, datetime.datetime.now(),)
            )
            url_id: int = cursor.fetchone().id
            flash('Страница успешно добавлена', 'success')

    conn.commit()
    conn.close()

    return redirect(url_for('url_get', id=url_id)), 301


@app.route('/urls/<int:id>')
def url_get(id):
    conn = connect_db()

    with conn.cursor(cursor_factory=NamedTupleCursor) as cursor:
        cursor.execute(
            'SELECT * FROM urls where id=%s', (id,)
        )
        url = cursor.fetchone()

        if not url:
            abort(404)

    with conn.cursor(cursor_factory=NamedTupleCursor) as cursor:
        cursor.execute(
            'SELECT * from url_checks '
            'where url_id=%s order by id desc', (id,)
        )

        checks = cursor.fetchall()

    conn.close()

    return render_template(
        'show.html',
        url=url,
        checks=checks
    )


@app.get('/urls')
def urls_get():
    conn = connect_db()
    with conn.cursor(cursor_factory=NamedTupleCursor) as cursor:
        cursor.execute(
            "SELECT * from urls order by id desc"
        )

        available_urls = cursor.fetchall()

        cursor.execute(
            "SELECT DISTINCT on (url_id) * from url_checks "
            "order by url_id desc, id desc"
        )

        checks = cursor.fetchall()

    conn.close()

    return render_template(
        'urls.html',
        data=list(zip(available_urls, checks)),
    )


@app.post('/urls/<id>/checks')
def url_check(id):
    conn = connect_db()

    with conn.cursor(cursor_factory=NamedTupleCursor) as cursor:
        cursor.execute(
            'SELECT * from urls where id=%s', (id,)
        )
        url = cursor.fetchone()

    try:
        response = requests.get(url.name)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        flash('Произошла ошибка при проверке', 'danger')
        return redirect(url_for('url_get', id=id))

    page_content = response.text
    page_content = page_parser(page_content)

    with conn.cursor(cursor_factory=NamedTupleCursor) as cursor:
        cursor.execute(
            'INSERT INTO url_checks (url_id, status_code, h1,'
            ' title, description, created_at) values '
            '(%s, %s, %s, %s, %s, %s)',
            (id, response.status_code, page_content.get('h1'),
             page_content.get('title'), page_content.get('description'),
             datetime.datetime.now(),)
        )
        flash('Страница успешно проверена', 'success')
    conn.commit()
    conn.close()

    return redirect(url_for('url_get', id=id))


@app.errorhandler(404)
def page_not_found(error):
    return 'Страница не найдена', 404


@app.errorhandler(500)
def server_error(error):
    return 'Ошибка сервера', 500
