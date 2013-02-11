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

from __future__ import absolute_import

from testmill.state import env


def get_images():
    """Return a list of all images."""
    if not hasattr(env, '_images'):
        images = env.api.get_images()
        # XXX: strip "TestMill:" prefix. Change this when we get
        # a hierarchical library structure.
        for image in images:
            if image['name'].startswith('TestMill:'):
                image['name'] = image['name'][9:]
        env._images = images
    return env._images


def get_applications():
    """Return a list of all applications."""
    if not hasattr(env, '_applications'):
        env._applications = env.api.get_applications()
    return env._applications


def get_blueprints():
    """Return a list of all blueprints."""
    if not hasattr(env, '_blueprints'):
        env._blueprints = env.api.get_blueprints()
    return env._blueprints


def get_image(id=None, name=None):
    """Get an image based on its id or name."""
    if id is None and name is None or \
                id is not None and name is not None:
        raise ValueError('Specify either "id" or "name" but not both.')
    for img in get_images():
        if name is not None:
            if name.lower() == img['name'].lower():
                return img
        elif id is not None:
            if img['id'] == id:
                return img


def get_application(id=None, name=None):
    """Get an application based on its id or name."""
    if id is None and name is None or \
                id is not None and name is not None:
        raise ValueError('Specify either "id" or "name" but not both.')
    for app in get_applications():
        if name is not None:
            if name.lower() == app['name'].lower():
                return app
        elif id is not None:
            if app['id'] == id:
                return app


def get_blueprint(id=None, name=None):
    """Get an application based on its id or name."""
    if id is None and name is None or \
                id is not None and name is not None:
        raise ValueError('Specify either "id" or "name" but not both.')
    for bp in get_blueprints():
        if name is not None:
            if name.lower() == bp['name'].lower():
                return bp
        elif id is not None:
            if bp['id'] == id:
                return bp


def get_full_image(id, force_reload=False):
    """Load one full image, possibly from cache."""
    if not hasattr(env, '_full_images'):
        env._full_images = {}
    img = env._full_images.get(id)
    if img is None or force_reload:
        img = env.api.get_image(id)
        # XXX: remove "TestMill:" prefix
        if img['name'].lower().startswith('testmill:'):
            img['name'] = img['name'][9:]
        env._full_images[id] = img
    return img


def get_full_application(id, force_reload=False):
    """Load one full application, possibly from cache."""
    if not hasattr(env, '_full_applications'):
        env._full_applications = {}
    app = env._full_applications.get(id)
    if app is None or force_reload:
        app = env.api.get_application(id)
        env._full_applications[id] = app
    return app


def get_full_blueprint(id, force_reload=False):
    """Load one full blueprint, possibly from cache."""
    if not hasattr(env, '_full_blueprints'):
        env._full_blueprints = {}
    bp = env._full_blueprints.get(id)
    if app is None or force_reload:
        bp = env.api.get_blueprint(id)
        env._full_blueprint[id] = bp
    return bp
