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


# Kudos to Jason Orendorff -
# http://stackoverflow.com/questions/2001138

def format_var(name, obj):
    if 'password' in name and isinstance(obj, str):
        obj = 'xxxxxxxx'
    res = repr(obj)
    if len(res) > 80 and not env.verbose:
        if isinstance(obj, list):
            noun = 'items' if len(obj) != 1 else 'item'
            res = '[<{} {}>]'.format(len(obj), noun)
        elif isinstance(obj, dict):
            noun = 'items' if len(obj) != 1 else 'item'
            res = '{{<{} {}>}}'.format(len(obj), noun)
        else:
            res = res[:60] + '...' + res[-1]
    return res

def stack_vars(stack):
    """Return a list of (name, value, depth) for all variables in
    the stack ``stack``."""
    result = []
    names = set()
    for scope in stack:
        for name in scope:
            names.add(name)
    def get_var(name):
        depth = len(stack)
        for scope in reversed(stack):
            depth -= 1
            if name in scope:
                return depth,scope[name]
    for name in sorted(names):
        if not name.startswith('__'):
            depth, value = get_var(name)
            result.append((name, format_var(name, value), depth))
    return result


class _Scope(object):
    """Context manager to enter a new scope."""

    def __init__(self, env, kwargs):
        self.env = env
        self.kwargs = kwargs

    def __enter__(self):
        self.env._stack.append(self.kwargs)

    def __exit__(self, *exc_info):
        # Keep an "exception stack". Immensely useful for debugging.
        if sys.exc_info()[1] and self.env._exc_ref is not sys.exc_info()[1]:
            # Need to keep a reference to the exception so that we know if
            # in the future we are handling a new exception or are still
            # unwinding scopes for the current one. Pretty bad...
            self.env._exc_ref = sys.exc_info()[1]
            self.env._exc_stack = self.env._stack[:]
        self.env._stack.pop()


class _Environment(object):
    """Shared state for TestMill. This class essentially provides LISP type
    dynamic binding using a context manager API to enter a new scope."""

    def __init__(self, **kwargs):
        self.__stack = [kwargs]
        self.__exc_ref = None
        self.__exc_stack = []

    @property
    def _stack(self):
        return self.__stack

    @property
    def _exc_ref(self):
        return self.__exc_ref

    @property
    def _exc_stack(self):
        return self.__exc_stack

    def __getattr__(self, name):
        for scope in reversed(self._stack):
            if name in scope:
                return scope[name]
        raise AttributeError(name)

    def __setattr__(self, name, value):
        private_prefix = '{}__'.format(self.__class__.__name__)
        if name.startswith(private_prefix):
            self.__dict__[name] = value
        else:
            self._stack[-1][name] = value

    def let(self, **kwargs):
        return _Scope(self, kwargs)

    def update(self, obj):
        for key in obj.__dict__:
            setattr(self, key, getattr(obj, key))

    def __repr__(self):
        clsname = self.__class__.__name__
        header = '<{}(), <depth={}>'.format(clsname, len(self._stack))
        show_exc_stack = sys.exc_info() and self._exc_stack
        if show_exc_stack:
            header += ', <exc_depth={}>'.format(len(self._exc_stack))
        header += '>'
        lines = [header]
        lines.append('  Current Environment:')
        for name,value,depth in stack_vars(self._stack):
            if not name.startswith('_') or self.verbose:
                lines.append('    {}[{}]: {}'.format(name, depth, value))
        if show_exc_stack:
            lines.append('  Exception Environment:')
            for name,value,depth in stack_vars(self._exc_stack):
                if not name.startswith('_') or self.verbose:
                    lines.append('    {}[{}]: {}'.format(name, depth, value))
        lines.append('')
        res = '\n'.join(lines)
        return res


env = _Environment()
