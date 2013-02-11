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

import time
import textwrap

from testmill import (console, login, manifest, keypair, util, cache,
                      inflect, application, error)


usage = textwrap.dedent("""\
        usage: ravtest [OPTION]... clean [-a]
               ravtest clean --help
        """)

description = textwrap.dedent("""\
        Clean up Ravello applications.
        
        This removes all non-running application instances of the current
        project. If --all is provided, then all non-running application
        instances of all projects are removed.

        The available options are:
            -a, --all
                Clean applications for all projects.
            -b, --blueprint
                Clean blueprints instead of applications.
        """)


def add_args(parser):
    parser.usage = usage
    parser.description = description
    parser.add_argument('-a', '--all', action='store_true')
    parser.add_argument('-b', '--blueprint', action='store_true')


def do_clean(args, env):
    """The "ravello clean" command."""
    with env.let(quiet=True):
        login.default_login()
        pubkey = keypair.default_keypair()
        manif = manifest.default_manifest(required=False)

    if manif is None and not args.all:
        error.raise_error('Project manifest ({0}) not found.\n'
                          'Cannot determine current project.\n'
                          "Use 'ravtest clean -a' to clean all projects.",
                          manifest.manifest_name())
    if args.all:
        project = None
    else:
        project = manif['project']['name']
        console.info('Project name is `{0}`.', project)
    
    if args.blueprint:
        objs = cache.get_blueprints(project)
        objs = filter(lambda app: app['state'] == 'DONE', objs)
        what = 'blueprint'
    else:
        objs = cache.get_applications(project)
        objs = filter(lambda app: app['totalStartedVms'] == 0, objs)
        what = 'application'

    count = len(objs)
    noun = inflect.plural_noun(what, count)
    if count == 0:
        console.info('There are no {0} to clean up.', noun)
        return 0

    if not env.always_confirm:
        console.warning('About to remove {0} {1}.', count, noun)
        console.warning('There is no way to undo this.')
        confirmed = console.confirm('Are you sure you want to continue?')
        if not confirmed:
            console.writeln('Not confirmed.')
            return 0

    for obj in objs:
        if args.blueprint:
            env.api.remove_blueprint(obj)
        else:
            env.api.remove_application(obj)

    verb = inflect.plural_verb('was', count)
    console.info('{0} {1} {2} succesfully removed.', count, noun, verb)
