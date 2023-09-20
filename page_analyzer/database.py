import os
import psycopg2
import datetime
from psycopg2.extras import NamedTupleCursor
from flask import abort, flash


def connect_db():
    db_url = os.getenv('DATABASE_URL')
    conn = psycopg2.connect(db_url)
    return conn


def get_url_by_name(url):
    conn = connect_db()
    with conn.cursor(cursor_factory=NamedTupleCursor) as cursor:
        cursor.execute(
            "SELECT * from urls where name=(%s)", (url,)
        )
        fetched_data = cursor.fetchone()
    conn.close()
    return fetched_data


def get_url_by_id(id):
    conn = connect_db()

    with conn.cursor(cursor_factory=NamedTupleCursor) as cursor:
        cursor.execute(
            'SELECT * from urls where id=%s', (id,)
        )
        url = cursor.fetchone()
    conn.close()
    return url


def get_url_with_checks(id):
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
    return url, checks


def add_url(url):
    conn = connect_db()
    with conn.cursor(cursor_factory=NamedTupleCursor) as cursor:
        cursor.execute(
            "INSERT INTO urls "
            "(name, created_at) "
            "VALUES (%s, %s) RETURNING id;",
            (url, datetime.datetime.now(),)
        )
        new_id = cursor.fetchone().id
    conn.commit()
    conn.close()
    return new_id


def add_check(id, response, page_content):
    conn = connect_db()

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


def get_urls():
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
    return available_urls, checks
