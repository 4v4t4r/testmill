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

from setuptools import setup

__version__ = '0.9.5.dev'


version_info = {
    'name': 'ravello-testmill',
    'version': __version__,
    'description': 'A system test driver for Ravello',
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


setup(
    package_dir = { '': 'lib' },
    packages = ['testmill'],
    install_requires = ['fabric>=1.5.1', 'pyyaml'],
    entry_points = {
        'console_scripts': ['ravtest = testmill.main:main']
    },
    package_data = {
        'testmill': ['*.yml']
    },
    **version_info
)
