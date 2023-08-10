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


load_dotenv()
app = Flask(__name__)
app.secret_key = os.urandom(12).hex()
DATABASE_URL = os.getenv('DATABASE_URL')


def normalize_url(url):
    o = urlparse(url)
    scheme = o.scheme
    name = o.netloc
    return f'{scheme}://{name}'


@app.route('/')
def index():
    return render_template(
        'index.html'
    )


@app.post('/urls')
def urls_post():
    url = request.form.to_dict()['url']
    norm_url = normalize_url(url)
    if validators.url(norm_url):

        today = datetime.datetime.now()
        created_at = datetime.date(today.year, today.month, today.day)
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute('SELECT name FROM urls')
        urls = [data[0] for data in cur.fetchall()]
        if norm_url not in urls:
            cur.execute('INSERT INTO urls (name, created_at) VALUES (%s, %s)',
                        (norm_url, created_at))
            conn.commit()
            cur.execute('SELECT id FROM urls WHERE name = (%s)', (norm_url,))
            site_id = cur.fetchone()[0]
            cur.close()
            conn.close()
            flash('Страница успешно добавлена', 'success')
        else:
            cur.execute('SELECT id FROM urls WHERE name = (%s)', (norm_url,))
            site_id = cur.fetchone()[0]
            flash('Страница уже существует', 'info')
            cur.close()
            conn.close()
        return redirect(url_for('url_get', id=site_id))
    else:
        flash('Некорректный url', 'danger')
        messages = get_flashed_messages(with_categories=True)
        return render_template(
            'index.html',
            messages=messages,
            url=url
        ), 422


@app.route('/urls/<int:id>')
def url_get(id):
    checks = []
    messages = get_flashed_messages(with_categories=True)
    conn = psycopg2.connect(DATABASE_URL)
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
    conn = psycopg2.connect(DATABASE_URL)
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
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    today = datetime.datetime.now()
    created_at = datetime.date(today.year, today.month, today.day)
    cur.execute('SELECT name FROM urls WHERE id = (%s)', (id,))
    url = cur.fetchone()[0]
    try:
        r = requests.get(url)
        r.raise_for_status()
        code = r.status_code

        soup = BeautifulSoup(r.text, 'html.parser')
        if soup.h1:
            h1 = soup.h1.string
        if soup.title:
            title = soup.title.string
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

    except requests.RequestException:
        flash('Произошла ошибка при проверке', 'danger')

    cur.close()
    conn.close()
    return redirect(url_for('url_get', id=id))
