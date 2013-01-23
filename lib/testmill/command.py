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
import getpass
import argparse


class AbortParsing(Exception):
    """Used by the "store_and_abort" action to abort parsing."""


class ArgumentParser(argparse.ArgumentParser):
    """An ArgumentParser that gives us more control over the
    formatting of the help texts.
    """

    class store_and_abort(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            if self.const is not None:
                setattr(namespace, self.dest, self.const)
            else:
                setattr(namespace, self.dest, values)
            raise AbortParsing(namespace)

    def format_help(self):
        parts = [self.usage, self.description]
        return '\n'.join(parts)

    def format_usage(self):
        return self.usage

    def parse_args(self, argv=None, namespace=None):
        try:
            args = super(ArgumentParser, self).parse_args(argv, namespace)
        except AbortParsing as e:
            args = e[0]
        return args


class CommandBase(object):
    """ABC for commands.
    
    Provides argument parsing, simple input/output, and sub-commands.
    """

    name = None
    usage = None
    description = None

    def __init__(self, parent=None):
        """Create a new command."""
        self.parent = parent
        self.sub_commands = []
        self.stdin = sys.stdin
        self.stdout = sys.stdout
        self.stderr = sys.stderr

    def add_sub_command(self, command):
        """Add a sub-command.
        
        The `command` argument must be a `Command` instance.
        """
        self.sub_commands.append(command)

    def add_args(self, parser, level=0):
        """Add command-line arguments to `parser`.

        This method should be extended by a subclass. The default
        implementation adds the parsers for the sub commands, if any.
        """
        if not self.sub_commands:
            return
        action = parser.add_subparsers(dest='__subcmd_{}'.format(level))
        for subcmd in self.sub_commands:
            parser = action.add_parser(subcmd.name, usage=subcmd.usage,
                                       description=subcmd.description)
            subcmd.add_args(parser, level+1)

    def read(self, prompt):
        """Prompt the user for a line of input."""
        return raw_input(prompt)

    def getpass(self, prompt):
        """Prompt the user for a password."""
        return getpass.getpass(prompt)

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
        """Run the command. Needs to be implemented by a subclass."""
        raise NotImplementedError

    def parse_args(self, argv=None, defaults=None):
        if sys.platform.startswith('win'):
            sys.argv[0] = sys.argv[0].rstrip('-script.py')
        parser = ArgumentParser(usage=self.usage, description=self.description)
        self.add_args(parser)
        args = parser.parse_args(argv, defaults)
        commands = []
        for name in dir(args):
            if not name.startswith('__subcmd_'):
                continue
            commands.append((int(name[9:]), getattr(args, name)))
            delattr(args, name)
        args.commands = [name for ix,name in sorted(commands)]
        return args

    def get_subcommand(self, commands):
        cmd = self
        for name in commands:
            for subcmd in cmd.sub_commands:
                if subcmd.name == name:
                    cmd = subcmd
                    break
            else:
                name = '/'.join(self.args.commands.names)
                self.error('sub command {} not found!'.format(name))
        return cmd

    def main(self, argv=None, defaults=None):
        """Main entry point."""
        try:
            args = self.parse_args(argv, defaults)
            cmd = self.get_subcommand(args.commands)
            self.sub_command = cmd
            cmd.args = args
            status = cmd.run(cmd.args)
        except SystemExit as e:
            status = e[0]
        if status is None:
            status = 0
        return status
