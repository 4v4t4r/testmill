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
import tempfile
import textwrap
import subprocess

from setuptools import setup


version_info = {
    'name': 'testmill',
    'version': '0.9.6.dev',
    'description': 'Create multi-VM application environments for dev/test.',
    'author': 'Geert Jansen',
    'author_email': 'geert.jansen@ravellosystems.com',
    'url': 'https://github.com/ravello/testmill',
    'license': 'Apache 2.0',
    'classifiers': [
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3'
    ]
}

topdir, _ = os.path.split(os.path.abspath(__file__))


def update_version():
    """Update the _version.py file."""
    fname = os.path.join('.', 'lib', 'testmill', '_version.py')
    try:
        with file(fname) as fin:
            current = fin.read()
    except IOError:
        current = None
    new = textwrap.dedent("""\
            # This file is autogenerated. Do not edit.
            version = '{0[version]}'
            version_string = 'Ravello TestMill {0[version]}'
            """.format(version_info))
    if current == new:
        return
    tmpname = '{0}.{1}-tmp'.format(fname, os.getpid())
    with file(tmpname, 'w') as fout:
        fout.write(new)
    os.rename(tmpname, fname)
    print('Updated _version.py')


def update_manifest():
    """Update the MANIFEST.in file from git, if necessary."""
    # It would be more efficient to create MANIFEST directly, rather
    # than creating a MANIFEST.in where every line just includes one file.
    # Unfortunately, setuptools/distribute do not support this (distutils
    # does).
    cmd = subprocess.Popen(['git', 'ls-tree', '-r', 'master', '--name-only'],
                           stdout=subprocess.PIPE)
    stdout, _ = cmd.communicate()
    files = stdout.splitlines()
    files.append('lib/testmill/_version.py')
    lines = ['include {0}\n'.format(fname)for fname in files]
    new = ''.join(sorted(lines))
    try:
        with file('MANIFEST.in', 'r') as fin:
            current = fin.read()
    except IOError:
        current = None
    if new == current:
        return
    tmpname = 'MANIFEST.in.{0}-tmp'.format(os.getpid())
    with file(tmpname, 'w') as fout:
        fout.write(new)
    os.rename(tmpname, 'MANIFEST.in')
    print('Updated MANIFEST.in')
    # Remove the SOURCES.txt that setuptools maintains. It appears not to
    # accurately regenerate it when MANIFEST.in changes.
    sourcestxt = os.path.join('lib', 'testmill.egg-info', 'SOURCES.txt')
    if not os.access(sourcestxt, os.R_OK):
        return
    os.unlink(sourcestxt)
    print('Removed {0}'.format(sourcestxt))


if __name__ == '__main__':
    os.chdir(topdir)
    update_version()
    update_manifest()
    setup(
        package_dir = { '': 'lib' },
        packages = ['testmill'],
        install_requires = ['fabric>=1.5.3', 'pyyaml'],
        entry_points = { 'console_scripts': ['ravtest = testmill.main:main'] },
        package_data = { 'testmill': ['*.yml'] },
        **version_info
    )
