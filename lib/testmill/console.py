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

import sys
import traceback
import getpass as getpass_

from testmill.state import env


def prompt(prompt):
    """Prompt the user for a line of input."""
    env._partial_line = True
    line = raw_input(prompt)
    env._partial_line = False
    return line

def confirm(message):
    """Ask the user for confirmation for an action."""
    message = '{0} (y/n): '.format(message)
    result = prompt(message)
    while result not in ('y', 'n'):
        info("Please enter 'y' or 'n'.")
        result = prompt(message)
    return result == 'y'

def getpass(prompt):
    """Prompt the user for a password."""
    env._partial_line = True
    passwd = getpass_.getpass(prompt)
    env._partial_line = False
    return passwd


def write(s):
    """Write a string to the console."""
    sys.stdout.write(s)

def writeln(s='', *args, **kwargs):
    """Write a string to the console, followed by a newline."""
    if args or kwargs:
        s = s.format(*args, **kwargs)
    write(s)
    write('\n')

def flush():
    """Flush standard outpout."""
    sys.stdout.flush()


def write_err(s):
    """Write a string to the console error stream."""
    sys.stderr.write(s)

def writeln_err(s=''):
    """Write a string to the console error stream, followed by a newline."""
    write_err(s)
    write_err('\n')

def flush_err(s):
    """Flush standard error."""
    sys.stderr.flush()


def start_progressbar(text):
    """Start a new progress bar with `text`."""
    env._progressbar_header = text
    env._progressbar_active = False

def show_progress(progress):
    """Show progress. Normally `progress` is a single character."""
    if env.quiet or not getattr(env, '_progressbar_header', False):
        return
    if not env._progressbar_active:
        env._partial_line = True
        write(env._progressbar_header)
        env._progressbar_active = True
    write(progress); flush()

def end_progressbar(text):
    """End a progress bar with "text"."""
    if getattr(env, '_progressbar_active', False):
        write(' {0}\n'.format(text))
    env._progressbar_header = None
    env._progressbar_active = False
    env._partial_line = False


def complete_partial_line():
    """Emit a newline to standard output if we are displaying a partial line.

    This is used when displaying output in an exception handler.
    """
    if getattr(env, '_partial_line', False):
        writeln()
    env._partial_line = False


def debug(message, *args, **kwds):
    """Show a debugging message."""
    if not env.debug:
        return
    if args or kwds:
        message = message.format(*args, **kwds)
    writeln_err(message)

def info(message, *args, **kwds):
    """Show an information message to the user."""
    if env.quiet:
        return
    if args or kwds:
        message = message.format(*args, **kwds)
    writeln_err(message)

def warning(message, *args, **kwds):
    """Show a warning."""
    if args or kwds:
        message = message.format(*args, **kwds)
    writeln_err('Warning: {0}'.format(message))

def error(message, *args, **kwds):
    """Trigger an error."""
    complete_partial_line()
    if args or kwds:
        message = message.format(*args, **kwds)
    writeln_err('Error: {0}'.format(message))

def show_exception(exc):
    error(str(exc))
    if not env.debug:
        return
    lines = ['An uncaught exception occurred:']
    lines += traceback.format_exception(*sys.exc_info())
    writeln_err()
    writeln_err(''.join(lines))
    writeln_err('Environment: {!r}'.format(env))
