# Copyright 2012-2013 Ravello Systems, Inc.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#    http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import json
import time
import struct
import socket
import urlparse
import httplib
import logging
import ssl

__all__ = ('random_luid', 'update_luids', 'RavelloError', 'RavelloClient')


def random_luid():
    rnd = os.urandom(7) + '\x00'
    luid = struct.unpack('<Q', rnd)[0]
    return luid

def update_luids(obj):
    """Update local UIDs on `obj'. NOTE: updates the object in-place!"""
    if isinstance(obj, dict):
        for key in obj:
            value = obj[key]
            if key == 'id':
                obj['id'] = random_luid()
            elif isinstance(value, dict) or isinstance(value, list):
                update_luids(value)
    elif isinstance(obj, list):
        for elem in obj:
            update_luids(elem)
    return obj


# The API client

class RavelloError(Exception):
    """Ravello error."""

    def __str__(self):
        if len(self.args) == 2:
            return '%s/%s' % (self.args[1], self.args[0])
        else:
            return self.args[0]


def should_retry(exc):
    """Return whether to retry an API call that raised exception `e'."""
    if isinstance(exc, socket.timeout):
        return True
    elif isinstance(exc, ssl.SSLError):
        # XXX: This is not a great way to check for a timeout.
        # However, e.errno is unset...
        return 'time' in exc.message
    return False

def idempotent(method):
    return method in ('GET', 'HEAD', 'PUT')


class RavelloClient(object):
    """Simple Ravello API client.

    TODO: just a quick hack, should use ravello library once that's released.
    """

    default_retries = 3
    default_timeout = 30
    default_url = 'https://cloud.ravellosystems.com/services'

    def __init__(self, username=None, password=None, service_url=None,
                 token=None, retries=None, timeout=None):
        """Create a new connection."""
        self.logger = logging.getLogger('testmill')
        self.username = username
        self.password = password
        self._set_url(service_url)
        self.token = token
        self.retries = retries or self.default_retries
        self.timeout = timeout or self.default_timeout
        self.connection = None
        self._cookie = None
        self._project = None
        self._total_retries = 0

    def __getstate__(self):
        """Pickle protocol."""
        state = self.__dict__.copy()
        state['logger'] = None
        if state['connection']:
            state['connection'] = True
        return state

    def __setstate__(self, state):
        """Pickle protocol."""
        self.__dict__.update(state)
        self.logger = logging.getLogger('ravello')
        if self.connection:
            self._connect()

    def __repr__(self):
        res = '<{0}({1!r})'.format(self.__class__.__name__, self.url)
        if self._cookie:
            res += ', <AUTHENTICATED>'
        elif self.connection:
            res += ', <CONNECTED>'
        else:
            res += ', <DISCONNECTED>'
        res += '>'
        return res

    def _set_url(self, url):
        """Parse and set the service URL."""
        if url is None:
            url = self.default_url
        parsed = urlparse.urlsplit(url)
        if parsed.scheme not in ('', 'http', 'https'):
            raise ValueError('unknown scheme: %s' % self.scheme)
        self.scheme = parsed.scheme or 'http'
        self.host = parsed.netloc
        self.path = parsed.path.rstrip('/')
        if parsed.port:
            self.port = parsed.port
        elif self.scheme == 'http':
            self.port = httplib.HTTP_PORT
        else:
            self.port = httplib.HTTPS_PORT
        self.url = url

    def _retry_request(self, method, url, body, headers):
        """Retry a request up to self.retry times."""
        log = self.logger
        for i in range(self.retries):
            try:
                if self.connection is None:
                    self._connect()
                    self._login()
                t1 = time.time()
                self.connection.request(method, url, body, dict(headers))
                response = self.connection.getresponse()
                response.body = response.read()
                t2 = time.time()
                log.debug('got response in {:.2f} secs'.format(t2-t1))
            except Exception as error:
                self.close()
                if not should_retry(error) or not idempotent(method):
                    raise
            else:
                return response
            self._total_retries += 1
            log.debug('operation timed out, reset connection and retry')
        log.debug('maximum retries reached, giving up')
        raise RavelloError('maximum retries reached making API call')

    def _make_request(self, method, url, body=None, headers=None):
        """Make a single HTTP request to the API and return the
        HTTPResponse object."""
        log = self.logger
        url = self.path + url
        if headers is None:
            headers = []
        headers.append(('User-Agent', 'TestMill/1.0'))
        headers.append(('Accept', 'application/json, */*'))
        if self._cookie is not None:
            headers.append(('Cookie', self._cookie))
        if body is None:
            body = ''
        else:
            body = json.dumps(body)
            headers.append(('Content-Type', 'application/json'))
        try:
            log.debug('API request: %s %s, %d bytes', method, url, len(body))
            response = self._retry_request(method, url, body, dict(headers))
        except (socket.error, ssl.SSLError, httplib.HTTPException) as e:
            log.error('error making API call: %s', str(e))
            raise RavelloError(str(e))
        body = response.body
        ctype = response.getheader('Content-Type')
        log.debug('API response: {0}, {1} bytes, ({2})' \
                .format(response.status, len(body), ctype))
        if 200 <= response.status < 300:
            if ctype == 'application/json':
                try:
                    parsed = json.loads(body)
                except Exception:
                    log.error('response body contains invalid JSON')
                    return
                response.entity = parsed
            else:
                response.entity = None
        elif response.status == 404 or (response.status == 500 and
                ('not found' in response.getheader('error-message', '')) or
                ('not exist' in response.getheader('error-message', '')) or
                ('was deleted' in response.getheader('error-message', ''))):
            # The second part of the clause above is completely bogus but
            # we need it until our API returns a 404 for a not found error.
            response.entity = None
        else:
            error = response.getheader('error-code')
            message = response.getheader('error-message', '')
            if error:
                log.debug('API detail: {0}: {1}'.format(error, message))
            if not message:
                message = 'API call failed with {0} {1}'\
                                .format(response.status, response.reason)
            raise RavelloError(message)
        return response

    def connect(self, url=None):
        """Connect to the API. NOTE: will not retry."""
        if self.connection is not None:
            raise RuntimeError('already connected')
        self._set_url(url)
        try:
            self._connect()
        except (socket.error, ssl.SSLError) as e:
            raise RavelloError('could not connect to API')

    def _connect(self):
        """Low-level connect."""
        log = self.logger
        if self.scheme == 'http':
            conn_class = httplib.HTTPConnection
        else:
            conn_class = httplib.HTTPSConnection
        connection = conn_class(self.host, self.port, timeout=self.timeout)
        log.debug('connecting to {0}:{1}...'.format(self.host, self.port))
        connection.connect()
        log.debug('connected')
        self.connection = connection

    def close(self):
        """Close the connection."""
        if self.connection:
            try:
                self.connection.close()
            except Exception:
                pass
        self.connection = None
        self._cookie = None

    def login(self, username=None, password=None, token=None):
        """Log in to the API."""
        if self._cookie is not None:
            raise RuntimeError('already logged in')
        if username is not None:
            if password is None:
                raise ValueError('username provided but not password')
            if token is not None:
                raise ValueError('cannot specify both username and token')
            self.username = username
            self.password = password
        elif token is not None:
            self.token = token
        self._login()

    def _login(self):
        """Low-level login."""
        log = self.logger
        if self.username:
            log.debug('performing a new login')
            auth = '%s:%s' % (self.username, self.password)
            auth = auth.encode('base64')
            headers = [('Authorization', 'Basic %s' % auth)]
            response = self._make_request('POST', '/login', headers=headers)
            # XXX: cookie hard-coded to be "JSESSIONID"
            cookies = response.getheader('Set-Cookie', '')
            for cookie in cookies.split(','):
                parts = [ part.strip() for part in cookie.split(';') ]
                if parts[0].startswith('JSESSIONID='):
                    self._cookie = parts[0]
                    log.debug('login: got JSESSIONID cookie')
                    break
            else:
                log.error('login: JSESSIONID cookie not found!')
                raise RavelloError('login failed')
        elif self.token:
            log.debug('logging in with token')
            self._cookie = self.token
            self.hello()  # Make sure the token works
            log.debug('token is valid')
        else:
            raise RuntimeError('cannot login: no username/password or token')
        # Also figure out the default project.
        if self._project is None:
            projects = self.get_projects()
            projects = sorted(projects, key=lambda pr: int(pr['id']))
            self._project = projects[0]['id']

    def logout(self):
        """Log out."""
        if self.connection is None:
            raise RuntimeError('not connected')
        self._make_request('POST', '/logout')  # will invalidate the token
        self._cookie = None

    def hello(self):
        self._make_request('GET', '/hello')

    # Users and projects

    def get_user(self):
        """Return the currently logged in user."""
        response = self._make_request('GET', '/user')
        return response.entity

    def get_project(self, id):
        """Return a single project."""
        response = self._make_request('GET', '/projects/%s' % id)
        return response.entity['project']

    def get_projects(self):
        """Return a list of all projects in the organization of the
        authenticating user.
        """
        response = self._make_request('GET', '/projects')
        projects = response.entity.get('project', [])
        return projects

    # Key pairs and public keys

    def get_pubkey(self, id):
        """Get a single public key."""
        # XXX: API missing, use get_pubkeys()
        pubkeys = self.get_pubkeys()
        for pubkey in pubkeys:
            if pubkey['id'] == id:
                return pubkey

    def get_pubkeys(self):
        """Get the public keys."""
        response = self._make_request('GET', '/keypairs/%s' % self._project)
        pubkeys = response.entity.get('keypair', [])
        return pubkeys

    def create_pubkey(self, pubkey):
        """Upload a public key."""
        request = pubkey.copy()
        request['projectId'] = self._project
        response = self._make_request('POST', '/keypair', request)
        return response.entity

    def create_keypair(self):
        """Create a newly generate keypair."""
        response = self._make_request('GET', '/keypair/random')
        return response.entity

    # Images (= saved VMs)

    def get_image(self, id):
        """Return a single image."""
        response = self._make_request('GET', '/images/%s' % id)
        if not response.entity:
            return
        return response.entity['value']

    def get_images(self):
        """Return a list of all images."""
        images = []
        response = self._make_request('GET', '/images/private')
        for image in response.entity.get('imageMetadata', []):
            images.append(dict(image, public=False))
        response = self._make_request('GET', '/images/public')
        for image in response.entity.get('imageMetadata', []):
            images.append(dict(image, public=True))
        return images

    # Applications

    def get_application(self, id):
        """Get a single application."""
        response = self._make_request('GET', '/instance/%s' % id)
        if not response.entity:
            return
        app = response.entity
        # TODO: does it make sense to have "appMetadata" be the "real"
        # application and put it at the top-level?
        for key in list(app['appMetadata']):
            app[key] = app['appMetadata'][key]
        del app['appMetadata']
        return app

    def get_applications(self):
        """Return all applications."""
        response = self._make_request('GET', '/instances/%s' % self._project)
        applications = response.entity.get('appMetadata', [])
        return applications

    def create_application(self, application, blueprint=None):
        """Create a new application."""
        if blueprint is not None:
            url = '/blueprint/{0}/instance/{1}' \
                        .format(blueprint['id'], application['name'])
            response = self._make_request('POST', url)
            application = response.entity
        else:
            application['appMetadata'] = {}
            for key in list(application):
                if key not in ('appMetadata', 'applicationLayer'):
                    application['appMetadata'][key] = application[key]
                    del application[key]
            response = self._make_request('POST', '/instance', application)
            application = response.entity
            for key in list(application['appMetadata']):
                application[key] = application['appMetadata'][key]
            del application['appMetadata']
        return application

    def publish_application(self, application, deploy=None):
        """Publish an application."""
        request = deploy.copy() if deploy else {}
        request['instanceId'] = application['id']
        self._make_request('POST', '/instance/publish', request)

    def remove_application(self, application):
        """Remove an application."""
        url = '/instance/{}'.format(application['id'])
        self._make_request('DELETE', url)

    # VMs

    def start_vm(self, application, vm):
        """Start a virtual machine."""
        url = '/deployment/app/%s/vm/%s/start' % (application['id'], vm['id'])
        self._make_request('POST', url)

    def stop_vm(self, application, vm):
        """Stop a virtual machine."""
        url = '/deployment/app/%s/vm/%s/stopguest' % (application['id'], vm['id'])
        self._make_request('POST', url)

    # Blueprints

    def get_blueprint(self, id):
        """Get a single blueprint."""
        response = self._make_request('GET', '/blueprint/%s' % id)
        if not response.entity:
            return
        bp = response.entity
        for key in list(bp['appMetadata']):
            bp[key] = bp['appMetadata'][key]
        del bp['appMetadata']
        return bp

    def get_blueprints(self):
        """Return all blueprints."""
        response = self._make_request('GET', '/blueprints/%s' % self._project)
        blueprints = response.entity.get('appMetadata', [])
        return blueprints

    def create_blueprint(self, name, application):
        """Create a new blueprint ``name`` based on ``application``."""
        offline = 'true'
        for vm in application.get('applicationLayer', {}).get('vm', []):
            if application['state'] != 'STOPPED':
                offline = 'false'
                break
        url = '/instance/{0}/blueprint/{1}/{2}' \
                    .format(application['id'], name, offline)
        response = self._make_request('POST', url)
        return response.entity

    def remove_blueprint(self, blueprint):
        """Remove a blueprint."""
        url = '/blueprint/{}'.format(blueprint['id'])
        self._make_request('DELETE', url)
