#
# Simple WSGI hello world app with database connectivity.

import httplib
import psycopg2

dsn = 'dbname=hello user=hello password=ravello host=db'


class connect_db(object):

    def __init__(self, dsn):
        self.dsn = dsn

    def __enter__(self):
        self.conn = psycopg2.connect(self.dsn)
        return self.conn

    def __exit__(self, *exc_info):
        self.conn.close()


def get_url(environ):
    """Return the request URL."""
    url = environ['SCRIPT_NAME'] + environ['PATH_INFO']
    qs = environ.get('QUERY_STRING')
    if qs:
        url += '?' + qs
    return url


def simple_response(start_response, code, body=None):
    status = '{0} {1}'.format(code, httplib.responses[code])
    headers = [('Content-Type', 'text/plain')]
    if isinstance(body, list):
        body = ''.join(body)
    elif not body:
        body = status
    headers.append(('Content-Length', str(len(body))))
    start_response(status, headers)
    return [body]


def hello_app(environ, start_response):
    url = get_url(environ)
    if url != '/':
        return simple_response(start_response, 404)
    with connect_db(dsn) as conn:
        cursor = conn.cursor()
        address = environ.get('REMOTE_ADDR')
        user_agent = environ.get('HTTP_USER_AGENT', '')
        request = '{0} {1}'.format(environ['REQUEST_METHOD'], url)
        cursor.execute('INSERT INTO visits '
                       'VALUES (DEFAULT, NOW(), %s, %s, %s)',
                       (address, request, user_agent))
        conn.commit()
        cursor.execute('SELECT count(*) FROM visits')
        total_visits = cursor.fetchone()[0]
        cursor.execute('SELECT * from VISITS ORDER BY datetime DESC LIMIT 10')
        last_visits = cursor.fetchall()
    body = ['Hello world!\n']
    body.append('Total visits: {0}\n'.format(total_visits))
    body.append('Last {0} visits:\n'.format(len(last_visits)))
    for visit in last_visits:
        dt = visit[1].strftime('%Y-%m-%d %H:%M:%S')
        body.append('  {0}  IP={1}  "{2}"  ({3})\n'.format(dt, *visit[2:]))
    return simple_response(start_response, 200, body)
