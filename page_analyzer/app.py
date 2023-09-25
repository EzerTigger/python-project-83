from flask import Flask, render_template, request, flash
from flask import redirect, url_for
import os
from dotenv import load_dotenv

from page_analyzer.urls import normalize_url, validate
from page_analyzer.parser import page_parser
from page_analyzer.requests import get_response
from page_analyzer.database import get_url_by_name, add_url, get_url_with_checks
from page_analyzer.database import get_urls, get_url_by_id, add_check

if "SECRET_KEY" not in os.environ:
    load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')


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

    fetched_data = get_url_by_name(url)
    if fetched_data:
        url_id: int = fetched_data.id
        flash('Страница уже существует', 'info')

    else:
        url_id: int = add_url(url)
        flash('Страница успешно добавлена', 'success')

    return redirect(url_for('url_get', id=url_id)), 301


@app.route('/urls/<int:id>')
def url_get(id):
    url, checks = get_url_with_checks(id)

    return render_template(
        'show.html',
        url=url,
        checks=checks
    )


@app.get('/urls')
def urls_get():
    available_urls, checks = get_urls()

    return render_template(
        'urls.html',
        data=list(zip(available_urls, checks)),
    )


@app.post('/urls/<id>/checks')
def url_check(id):
    url = get_url_by_id(id)
    response = get_response(url.name)
    if not response:
        return redirect(url_for('url_get', id=id))

    page_content = response.text
    page_content = page_parser(page_content)

    add_check(id, response, page_content)

    return redirect(url_for('url_get', id=id))


@app.errorhandler(404)
def page_not_found(error):
    return render_template('error/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('error/500.html'), 500
