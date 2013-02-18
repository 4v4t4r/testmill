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

from __future__ import absolute_import, print_function

import os
import copy
import fnmatch
import yaml

import testmill
from testmill import cache, console, validate, error, util, versioncontrol
from testmill.state import env


class ParseError(RuntimeError):
    """Manifest parse error."""

ValidationError = validate.ValidationError


def merge(source, dest, only_key=None):
    """Merge the dictionary ``source`` onto ``dest``."""
    for key,value in source.items():
        if key not in dest:
            dest[key] = copy.deepcopy(value)
        elif isinstance(value, dict) and isinstance(dest[key], dict):
            merge(value, dest[key])


def default_manifest_name():
    """Return the default manifest name."""
    return '.ravello.yml'


def manifest_name():
    """Return the actual manifest name."""
    if env.manifest:
        return env.manifest
    return default_manifest_name()


def manifest_exists(filename=None):
    """Return whether the manifest exists."""
    if filename is None:
        filename = manifest_name()
    return os.access(filename, os.R_OK)


def load_manifest(filename=None):
    """Load the project manifest, merge in the default manifest,
    and return the result."""
    if filename is None:
        filename = manifest_name()
    if not manifest_exists(filename):
        error.raise_error('Project manifest ({0}) not found.', filename)
    with file(filename) as fin:
        try:
            manifest = yaml.load(fin)
        except yaml.error.YAMLError as e:
            if env.verbose:
                error.raise_error('Illegal YAML in manifest.\n'
                                  'Message from parser: {!s}', e)
            else:
                error.raise_error('Illegal YAML in manifest.\n'
                                  'Try --verbose for more information.')
    manifest['_filename'] = filename
    directory, _ = os.path.split(os.path.abspath(filename))
    _, project = os.path.split(directory)
    manifest['_directory'] = directory
    packagedir = testmill.packagedir()
    filename = os.path.join(packagedir, 'defaults.yml')
    with file(filename) as fin:
        defaults = yaml.load(fin)
    merge(defaults, manifest)
    env.manifest = manifest
    return manifest


def detect_language(manifest, directory='.'):
    """Dectect the language of a project directory."""
    files = os.listdir(directory)
    languages = manifest.get('languages', {})
    def fnmatch_any(files, patterns):
        for fname in files:
            for pattern in patterns:
                if fnmatch.fnmatch(fname, pattern):
                    return True
        return False
    for language in languages:
        patterns = languages[language].get('detect', [])
        if fnmatch_any(files, patterns):
            break
    else:
        language = None
    return language


def add_defaults(manifest):
    """Add defaults to manifest."""
    directory = manifest['_directory']
    manifest.setdefault('project', {})
    name = manifest['project'].get('name')
    if name is None:
        _, name = os.path.split(directory)
        console.info("Using '{0}' as the project name.", name)
        manifest['project']['name'] = name
    language = manifest['project'].get('language')
    if language is None:
        language = detect_language(manifest, directory)
        if language:
            console.info("Detected a {0} project.", language)
    manifest['project']['language'] = language
    if language and language not in manifest.get('languages', {}):
        console.warning("Unknown language '{0}' in manifest.", language)
    repo = manifest.setdefault('repository', {})
    typ = repo.get('type')
    if typ is None:
        typ = versioncontrol.detect_type(directory)
        if typ:
            console.info('Detected a {0} repository.', typ)
    repo['type'] = typ
    url = repo.get('url')
    if url is None and typ:
        url = versioncontrol.get_origin(directory, typ)
        if url:
            console.info("Using remote origin '{0}'.", url)
    repo['url'] = url
    manifest.setdefault('defaults', {})
    manifest.setdefault('languages', {})
    manifest.setdefault('applications', [])


def percolate_defaults(manifest):
    """Percolate the default settings defined in ``manifest``.

    The defaults are specified under the ``defaults:`` and the
    ``languages/$language:`` keys. They are percolated to the applications,
    vms and tasks definitions under ``applications:``.
    """
    defaults = manifest['defaults']
    language = manifest.get('language')
    if language:
        manifest['project']['language'] = language
        del manifest['language']
    language = manifest['project']['language']
    langdefs = manifest['languages'].get(language, {})
    for appdef in manifest['applications']:
        merge(langdefs.get('applications', {}), appdef)
        merge(defaults.get('applications', {}), appdef)
        for vmdef in appdef.get('vms', []):
            merge(langdefs.get('vms', {}), vmdef)
            merge(defaults.get('vms', {}), vmdef)
            for taskdef in vmdef.get('tasks', []):
                merge(langdefs.get('tasks', {}), taskdef)
                merge(defaults.get('tasks', {}), taskdef)
    if 'defaults' in manifest:
        del manifest['defaults']
    if 'languages' in manifest:
        del manifest['languages']
    return manifest


def expand_shorthands(manifest):
    """Expand shorthand notation in the manifest.

    The short hand notation allows you to write tasks more compactly.
    The manifest is updated, and also returned.
    """
    for appdef in manifest.get('applications', []):
        for vmdef in appdef.get('vms', []):
            for taskdef in vmdef.get('tasks', []):
                name = taskdef.get('name')
                if name in vmdef:
                    commands = vmdef[name]
                elif name in appdef:
                    commands = appdef[name]
                else:
                    continue
                commands = copy.deepcopy(commands)
                if isinstance(commands, str):
                    taskdef['commands'] = [commands]
                elif isinstance(commands, list):
                    taskdef['commands'] = commands
                elif isinstance(commands, dict):
                    taskdef.update(commands)
    for appdef in manifest.get('applications', []):
        for vmdef in appdef.get('vms', []):
            for taskdef in vmdef.get('tasks', []):
                name = taskdef.get('name')
                if name in vmdef:
                    del vmdef[name]
                if name in appdef:
                    del appdef[name]
    return manifest


def complete_data(manifest):
    """Complete the final pieces of data."""
    for appdef in manifest.get('applications', []):
        blueprint = appdef.get('blueprint')
        for vmdef in appdef.get('vms', []):
            if 'image' not in vmdef and not blueprint:
                vmdef['image'] = vmdef['name']


def check_manifest(manifest):
    """Check a manifest for validity.

    A permissive approach is taken whereby only known keys need to
    confirm to our specification and unknown keys are ignored.
    """
    def check(path, check):
        try:
            validate.validate_node(manifest, path, check)
        except validate.ValidationError as e:
            path = validate.pathref(e[1])
            error.raise_error('{0}: {1}: {2}', manifest['_filename'], path, e[0])

    check('/project', dict)
    check('/project/name', str)
    check('/project/language', str)
    check('/repository', dict)
    check('/repository/type', str)
    check('/repository/url', str)
    check('/applications', list)
    check('/applications/*', (str, dict))
    check('/applications/*/!name', str)
    check('/applications/*/blueprint', str)
    check('/applications/*/vms', list)
    check('/applications/*/vms/*', (str, dict))
    check('/applications/*/vms/*/!name', str)
    check('/applications/*/vms/*/image', str)
    check('/applications/*/vms/*/memory', int)
    check('/applications/*/vms/*/tasks', list)
    check('/applications/*/vms/*/tasks/*', (str, dict))
    check('/applications/*/vms/*/tasks/*/!name', str)
    check('/applications/*/vms/*/tasks/*/class', str)
    check('/applications/*/vms/*/tasks/*/commands', list)
    check('/defaults', dict)
    check('/defaults/vms', dict)
    check('/defaults/vms/tasks', list)
    check('/defaults/vms/tasks/*', dict)
    check('/defaults/vms/tasks/*/!name', str)
    check('/defaults/vms/tasks/*/class', str)
    check('/defaults/vms/tasks/*/commands', list)
    check('/languages', dict)
    check('/languages/*', dict)
    check('/languages/*/detect', list)
    check('/languages/*/vms', dict)
    check('/languages/*/vms/tasks', list)
    check('/languages/*/vms/tasks/*', dict)
    check('/languages/*/vms/tasks/*/!name', str)
    check('/languages/*/vms/tasks/*/class', str)
    check('/languages/*/vms/tasks/*/commands', list)


def check_manifest_entities(manifest):
    """Check that the entities referenced from ``manifest`` exist.

    On error, a ValidationError is raised with a two arguments: an
    appropriate error message and the node path that caused the error.
    """
    def blueprint_exists(name, nodepath):
        if not cache.get_blueprint(name=name):
            msg = 'Blueprint `{0}` does not exist.'.format(name)
            raise validate.ValidationError(msg, nodepath)
        return True

    def image_exists(name, nodepath):
        if not cache.get_image(name=name):
            msg = 'Image `{0}` does not exist.'.format(name)
            raise validate.ValidationError(msg, nodepath)
        return True

    def can_load_class(name):
        return bool(util.load_class(name))

    def check(path, check):
        try:
            validate.validate_node(manifest, path, check)
        except validate.ValidationError as e:
            path = validate.pathref(e[1])
            error.raise_error('{0}:{1}: {2}', manifest['_filename'], path, e[0])

    check('/applications/*/blueprint', blueprint_exists)
    check('/applications/*/vms/*/image', image_exists)
    check('/applications/*/tasks/*/class', can_load_class)
    check('/defaults/vms/tasks/*/class', can_load_class)
    check('/languages/*/vms/tasks/*/class', can_load_class)


def default_manifest(required=True):
    """The default process of bootstrapping and checking the manifest."""
    filename = env.manifest
    if not filename:
        filename = default_manifest_name()
        if not manifest_exists(filename) and not required:
            return
    manifest = load_manifest(filename)
    check_manifest(manifest)
    add_defaults(manifest)
    percolate_defaults(manifest)
    expand_shorthands(manifest)
    complete_data(manifest)
    check_manifest_entities(manifest)
    return manifest
