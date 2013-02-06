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

import textwrap
from testmill import console, manifest, login, validate, util


usage = textwrap.dedent("""\
        usage: ravtest [OPTION]... lint [--check-entities] [--dump]
               ravtest lint --help
        """)

description = textwrap.dedent("""\
        Check the format of a project manifest ({manifest_name}).

        By default, only the syntax of the manifest is checked. However,
        when the --check-entities option is provided, the existence of
        entities that are referenced in the manifest (images, blueprints,
        and task files) is checked as well. NOTE that using this option
        requires a connection to the Ravello Service. You should be logged
        in with "ravtest login" command, or you should pass the -u and -p
        parameters.

        The available options are:
            --check-entities
                In addition to the syntax of the manifest, also check
                that the referenced entities exist.
            --dump
                Dump the manifest after it has been validated.
        """.format(manifest_name=manifest.manifest_name()))


def add_args(parser):
    parser.usage = usage
    parser.description = description
    parser.add_argument('--check-entities', action='store_true')
    parser.add_argument('--dump', action='store_true')


def do_lint(args, env):
    """The "ravtest lint" command."""
    if args.check_entities:
        login.default_login()
    console.info('Checking manifest...')
    manif = manifest.load_manifest()
    manifest.check_manifest(manif)
    manifest.add_defaults(manif)
    manifest.percolate_defaults(manif)
    manifest.expand_shorthands(manif)
    manifest.complete_data(manif)
    if args.check_entities:
        manifest.check_manifest_entities(manif)
    console.info('Manifest OK')
    if args.dump:
        console.write(util.prettify(manif))
