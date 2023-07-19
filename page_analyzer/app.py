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
        else:
            cur.execute('SELECT id FROM urls WHERE name = (%s)', (url,))
            site_id = cur.fetchone()[0]
            flash('Страница уже существует', 'warning')
        return redirect(url_for('url_get', id=site_id))
    else:
        flash('Некорректный url', 'error')
        return redirect('/')


@app.route('/urls/<id>')
def url_get(id):
    messages = get_flashed_messages()
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute('SELECT * FROM urls WHERE id = (%s)', (id,))
    site_id, site_name, site_created_at = cur.fetchone()
    cur.close()
    conn.close()
    return render_template(
        'show.html',
        site_id=site_id,
        site_name=site_name,
        site_created_at=site_created_at,
        messages=messages,
    )


@app.route('/urls/')
def urls_get():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute('SELECT * FROM urls ORDER BY created_at DESC')
    sites = cur.fetchall()
    cur.close()
    conn.close()
    return render_template(
        'urls.html',
        sites=sites
    )
