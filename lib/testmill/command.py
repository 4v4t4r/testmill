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

import sys
import argparse


class ArgumentParser(argparse.ArgumentParser):
    """An ArgumentParser that gives us more control over the
    formatting of the help texts.
    """

    class show_help(argparse.Action):
        def __call__(self, parser, ns, vals, opts):
            if not getattr(ns, 'command', None):
                parser.print_help()
                parser.exit(0)
            ns.help = True

    def format_help(self):
        parts = [self.usage, self.description]
        return '\n'.join(parts)

    def format_usage(self):
        return self.usage


class CommandBase(object):
    """ABC for commands.
    
    Provides argument parsing, simple input/output, and sub-commands.
    """

    name = None
    usage = None
    description = None

    def __init__(self):
        """Create a new command."""
        self.sub_commands = []
        self.stdin = sys.stdin
        self.stdout = sys.stdout
        self.stderr = sys.stderr

    def add_sub_command(self, command):
        """Add a sub-command.
        
        The `command` argument must be a `Command` instance.
        """
        self.sub_commands.append(command)

    def add_args(self, parser):
        """Add command-line arguments to `parser`.

        This method should be provided by a subclass. The default
        implementation adds a positional argument "command" if there are
        sub-commands.
        """
        if not self.sub_commands:
            return
        parser.add_argument('command')

    def parse_args(self, args=None, defaults=None):
        """Parse arguments."""
        parser = ArgumentParser(usage=self.usage, description=self.description,
                                add_help=False)
        parser.add_argument('-h', '--help', action=parser.show_help, nargs=0)
        self.add_args(parser)
        if defaults and defaults.help:
            args.insert(0, '--help')
        args, remaining = parser.parse_known_args(args)
        if remaining and not self.sub_commands:
            parser.error('unrecognized arguments: %s' % ' '.join(remaining))
        if defaults:
            defaults.__dict__.update(args.__dict__)
            args = defaults
        self.args = args
        self.remaining = remaining
        self.parser = parser

    def read(self, prompt):
        """Prompt the user for a line of input."""
        return raw_input(prompt)

    def write(self, message):
        """Write a line of text to standard output."""
        self.stdout.write(message)
        self.stdout.write('\n')

    def error(self, message):
        """Write a line of text to standard error."""
        self.stderr.write(message)
        self.stderr.write('\n')

    def exit(self, status):
        """Exit with exit status `status`."""
        sys.exit(status)

    def run(self, args):
        """Run the command.
        
        This method needs to be provided by a subclass. However, in case there
        are sub-commands, there is a default implementation that just calls
        into the right sub-command.
        """
        if not self.sub_commands:
            raise NotImplementedError
        command = args.command
        for subcmd in self.sub_commands:
            if subcmd.name == command:
                subcmd.parse_args(self.remaining, args)
                subcmd.run(subcmd.args)
                break
        else:
            self.error('Error: no such command: %s' % command)
