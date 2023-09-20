from flask import Flask, render_template, request, flash
from flask import redirect, url_for, abort
import psycopg2
import os
import datetime
from dotenv import load_dotenv
from psycopg2.extras import NamedTupleCursor

from page_analyzer.urls import normalize_url, validate
from page_analyzer.parser import page_parser
from page_analyzer.requests import get_response


load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
app.config['DATABASE_URL'] = os.getenv('DATABASE_URL')


def connect_db():
    conn = psycopg2.connect(app.config['DATABASE_URL'])
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

    response = get_response(url.name)
    if not response:
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
    return render_template('error/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('error/500.html'), 500
