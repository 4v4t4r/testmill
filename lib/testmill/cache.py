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


def _fixup_image(image):
    # XXX: Strip TestMill: prefix. We keep the testmill images with this
    # prefix until we've got a hierarchical library structure where we
    # can put them.
    if image['name'].startswith('TestMill:'):
        image['name'] = image['name'][9:]


def _init_image_cache():
    """Initialize the images cache."""
    if hasattr(env, '_images'):
        return
    images = env.api.get_images()
    for image in images:
        _fixup_image(image)
    env._images = images
    env._images_byid = {}
    env._images_byname = {}


def get_images():
    """Return a list of all images."""
    _init_image_cache()
    return env._images


def get_image(id=None, name=None):
    """Get an image based on its id or name."""
    _init_image_cache()
    if id:
        img = env._images_byid.get(id)
        if img is not None:
            return img
        img = env.api.get_image(id)
        _fixup_image(img)
        env._images_byid[img['id']] = img
        env._images_byname[img['name']] = img
        return img
    elif name:
        img = env._images_byname.get(name)
        if img is not None:
            return img
        for img in env._images:
            if img['name'] == name:
                break
        else:
            return
        img = env.api.get_image(img['id'])
        _fixup_image(img)
        env._images_byid[img['id']] = img
        env._images_byname[img['name']] = img
        return img
    else:
        raise ValueError('Specifiy either "id" or "name".')


def _init_application_cache():
    """Initialize the applications cache."""
    if hasattr(env, '_applications'):
        return
    env._applications = env.api.get_applications()
    env._applications_byid = {}
    env._applications_byname = {}


def get_applications():
    """Return a list of all applications."""
    _init_application_cache()
    return env._applications


def find_applications(project=None, defname=None, instance=None):
    """Find one or more applications."""
    _init_application_cache()
    applications = []
    for app in env._applications:
        parts = app['name'].split(':')
        if len(parts) != 3:
            continue
        if project is not None and parts[0] != project or \
                defname is not None and parts[1] != defname or \
                instance is not None and parts[2] != instance:
            continue
        applications.append(app)
    return applications


def get_application(id=None, name=None, force_reload=False):
    """Get an application based on its id or name."""
    _init_application_cache()
    if force_reload:
        env._applicatons = env.api.get_applications()
    if id:
        if not force_reload:
            app = env._applications_byid.get(id)
            if app is not None:
                return app
        app = env.api.get_application(id)
        if app:
            env._applications_byid[app['id']] = app
            env._applications_byname[app['name']] = app
        elif force_reload and id in env._applications_byid:
            oldapp = env._applications_byid[id]
            del env._applications_byid[oldapp['id']]
            del env._applications_byname[oldapp['name']]
        return app
    elif name:
        if not force_reload:
            app = env._applications_byname.get(name)
            if app is not None:
                return app
        for app in env._applications:
            if app['name'] == name:
                break
        else:
            return
        app = env.api.get_application(app['id'])
        if app:
            env._applications_byid[app['id']] = app
            env._applications_byname[app['name']] = app
        elif force_reload and name in env._applications_byname:
            oldapp = env._applications_byname[name]
            del env._applications_byid[oldapp['id']]
            del env._applications_byname[oldapp['name']]
        return app
    else:
        raise ValueError('Specifiy either "id" or "name".')


def _init_blueprint_cache():
    """Initialize the blueprints cache."""
    if hasattr(env, '_blueprints'):
        return
    env._blueprints = env.api.get_blueprints()
    env._blueprints_byid = {}
    env._blueprints_byname = {}


def get_blueprints():
    """Return a list of all blueprints."""
    _init_blueprint_cache()
    return env._blueprints


def find_blueprints(project=None, defname=None, instance=None):
    """Find one or more blueprints."""
    _init_blueprint_cache()
    blueprints = []
    for bp in env._blueprints:
        parts = bp['name'].split(':')
        if len(parts) != 3:
            continue
        if project is not None and parts[0] != project or \
                defname is not None and parts[1] != defname or \
                instance is not None and parts[2] != instance:
            continue
        blueprints.append(bp)
    return blueprints


def get_blueprint(id=None, name=None, force_reload=False):
    """Get an blueprint based on its id or name."""
    _init_blueprint_cache()
    if force_reload:
        env._blueprints = env.api.get_blueprints()
    if id:
        if not force_reload:
            bp = env._blueprints_byid.get(id)
            if bp is not None:
                return bp
        bp = env.api.get_blueprint(id)
        if bp:
            env._blueprints_byid[bp['id']] = bp
            env._blueprints_byname[bp['name']] = bp
        elif force_reload  and id in env._blueprints_byid:
            oldbp = env._blueprints_byid[id]
            del env._blueprints_byid[oldbp['id']]
            del env._blueprints_byname[oldbp['name']]
        return bp
    elif name:
        if not force_reload:
            bp = env._blueprints_byname.get(name)
            if bp is not None:
                return bp
        for bp in env._blueprints:
            if bp['name'] == name:
                break
        else:
            return
        bp = env.api.get_blueprint(bp['id'])
        if bp:
            env._blueprints_byid[bp['id']] = bp
            env._blueprints_byname[bp['name']] = bp
        elif force_reload  and name in env._blueprints_byname:
            oldbp = env._blueprints_byname[name]
            del env._blueprints_byid[oldbp['id']]
            del env._blueprints_byname[oldbp['name']]
        return bp
    else:
        raise ValueError('Specifiy either "id" or "name".')
