from flask import Flask, render_template, request, flash, get_flashed_messages
from flask import redirect, url_for
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
app.secret_key = os.urandom(12).hex()
DATABASE_URL = os.getenv('DATABASE_URL_DEV')


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
    conn = psycopg2.connect(DATABASE_URL)
    return conn


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
    checks = []
    messages = get_flashed_messages(with_categories=True)
    conn = connect_db()
    cur = conn.cursor()
    cur.execute('SELECT * FROM urls WHERE id = (%s)', (id,))
    site_id, site_name, site_created_at = cur.fetchone()
    cur.execute('SELECT id, status_code, h1, title, description, created_at '
                'FROM url_checks WHERE url_id = (%s)',
                (id,))
    data = cur.fetchall()
    if data:
        checks = data
    cur.close()
    conn.close()
    return render_template(
        'show.html',
        site_id=site_id,
        site_name=site_name,
        site_created_at=site_created_at,
        checks=checks,
        messages=messages,
    )


@app.get('/urls')
def urls_get():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute('SELECT urls.id AS url_id, urls.name AS url_name, '
                'MAX(url_checks.created_at) AS check_created_at,'
                'url_checks.status_code AS status_code FROM urls '
                'LEFT JOIN url_checks ON urls.id = url_checks.url_id '
                'GROUP BY urls.id, url_checks.status_code '
                'ORDER BY urls.created_at DESC')
    sites = cur.fetchall()
    cur.close()
    conn.close()
    return render_template(
        'urls.html',
        sites=sites
    )


@app.post('/urls/<id>/checks')
def url_check(id):
    h1 = ''
    title = ''
    description = ''
    conn = connect_db()
    cur = conn.cursor()
    today = datetime.datetime.now()
    created_at = datetime.date(today.year, today.month, today.day)
    cur.execute('SELECT name FROM urls WHERE id = (%s)', (id,))
    url = cur.fetchone()[0]
    try:
        r = requests.get(url)
        r.raise_for_status()
        code = r.status_code
        if code != 200:
            flash('Произошла ошибка при проверке', 'danger')
            return redirect(url_for('url_get', id=id))
        else:
            soup = BeautifulSoup(r.text, 'html.parser')
            if soup.h1:
                h1 = soup.h1.text
            if soup.title:
                title = soup.title.text
            meta = soup.find('meta', attrs={'name': 'description'})
            if meta:
                description = meta.get('content')
            cur.execute('INSERT INTO url_checks '
                        '(url_id, status_code, '
                        'h1, title, description, created_at) '
                        'VALUES (%s, %s, %s, %s, %s, %s)',
                        (id, code, h1, title, description, created_at))
            conn.commit()
            flash('Страница успешно проверена', 'success')
            return redirect(url_for('url_get', id=id))
    except Exception:
        flash('Произошла ошибка при проверке', 'danger')
        return redirect(url_for('url_get', id=id))
    finally:
        cur.close()
        conn.close()


@app.errorhandler(404)
def page_not_found(error):
    return 'Страница не найдена', 404


@app.errorhandler(500)
def server_error(error):
    return 'Ошибка сервера', 500
