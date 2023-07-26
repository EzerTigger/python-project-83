from flask import Flask, render_template, request, flash, get_flashed_messages
from flask import redirect, url_for
import psycopg2
import os
import datetime
import validators
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.secret_key = os.urandom(12).hex()
DATABASE_URL = os.getenv('DATABASE_URL')


@app.route('/')
def index():
    messages = get_flashed_messages(with_categories=True)
    return render_template(
        'index.html',
        messages=messages
    )


@app.post('/urls/')
def urls_post():
    url = request.form.to_dict()['url']
    if validators.url(url):
        today = datetime.datetime.now()
        created_at = datetime.date(today.year, today.month, today.day)
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute('SELECT name FROM urls')
        urls = [data[0] for data in cur.fetchall()]
        if url not in urls:
            cur.execute('INSERT INTO urls (name, created_at) VALUES (%s, %s)',
                        (url, created_at))
            conn.commit()
            cur.execute('SELECT id FROM urls WHERE name = (%s)', (url,))
            site_id = cur.fetchone()[0]
            cur.close()
            conn.close()
            flash('Страница успешно добавлена', 'success')
        else:
            cur.execute('SELECT id FROM urls WHERE name = (%s)', (url,))
            site_id = cur.fetchone()[0]
            flash('Страница уже существует', 'info')
        return redirect(url_for('url_get', id=site_id))
    else:
        flash('Некорректный url', 'error')
        return redirect('/')


@app.route('/urls/<id>')
def url_get(id):
    checks = []
    messages = get_flashed_messages(with_categories=True)
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute('SELECT * FROM urls WHERE id = (%s)', (id,))
    site_id, site_name, site_created_at = cur.fetchone()
    cur.execute('SELECT id, created_at FROM url_checks WHERE url_id = (%s)',
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


@app.route('/urls/')
def urls_get():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute('SELECT urls.id AS url_id, urls.name AS url_name, '
                'MAX(url_checks.created_at) AS check_created_at FROM urls '
                'LEFT JOIN url_checks ON urls.id = url_checks.url_id '
                'GROUP BY urls.id ORDER BY urls.created_at DESC')
    sites = cur.fetchall()
    cur.close()
    conn.close()
    return render_template(
        'urls.html',
        sites=sites
    )


@app.post('/urls/<id>/checks')
def url_check(id):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    today = datetime.datetime.now()
    created_at = datetime.date(today.year, today.month, today.day)
    cur.execute('INSERT INTO url_checks (url_id, created_at) VALUES (%s, %s)',
                (id, created_at))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('url_get', id=id))
