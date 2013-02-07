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
        depth, value = get_var(name)
        result.append((name, format_var(name, value), depth))
    return result


class _Scope(object):
    """Context manager to enter a new scope."""

    def __init__(self, env, kwargs):
        self.env = env
        self.kwargs = kwargs

    def __enter__(self):
        envdata = self.env.__dict__
        envdata['__stack'].append(self.kwargs)

    def __exit__(self, *exc_info):
        # Keep an "exception stack". Immensely useful for debugging.
        envdata = self.env.__dict__
        if sys.exc_info()[1] and envdata['__exc_ref'] is not sys.exc_info()[1]:
            # Need to keep a reference to the exception so that we know if
            # in the future we are handling a new exception or are still
            # unwinding scopes for the current one. Pretty bad...
            envdata['__exc_ref'] = sys.exc_info()[1]
            envdata['__exc_stack'] = envdata['__stack'][:]
        envdata['__stack'].pop()

    start = __enter__
    stop = __exit__


class _Swapper(object):

    def __init__(self, cur, new):
        self._cur = cur
        self._new = new

    def __enter__(self):
        tmp = self._cur.__dict__
        self._cur.__dict__ = self._new.__dict__
        self._new.__dict__ = tmp

    def __exit__(self, *exc_info):
        tmp = self._cur.__dict__
        self._cur.__dict__ = self._new.__dict__
        self._new.__dict__ = tmp


class _Environment(object):
    """Shared state for TestMill.
    
    This class manages for a global shared state with static and stack-wise
    dynamic binding.

    It is modeled closely after Clojure's dynamic binding of Vars. In summary:

      env.foo = 10      # Create a new dynamic variable 'foo' with value 10
                        # The value is assigned to the global scope.
      env._foo = 10     # Create a new static variable. The value is assigned
                        # to the global scope. It may not be re-bound in a sub
                        # scope.
      env.let(foo=20)   # enter a new scope, in which 'foo' = 20.
      print(env.foo)    # print the value of 'foo' in the current scope, or any
                        # parent scope, until the variable is found.
      print(env._foo)   # print the value of '_foo'. Since _foo is static, it
                        # will always be in the root scope.
    """

    def __init__(self, **kwargs):
        self.__dict__['__stack'] = [kwargs]
        self.__dict__['__exc_ref'] = None
        self.__dict__['__exc_stack'] = []

    def __getattr__(self, name):
        stack = self.__dict__['__stack']
        for scope in reversed(stack):
            if name in scope:
                return scope[name]
        raise AttributeError(name)

    def __setattr__(self, name, value):
        """Set a global variable in this environment."""
        stack = self.__dict__['__stack']
        stack[0][name] = value

    def let(self, **kwargs):
        """Enter a new scope, and set all variables in ``kwargs`` as local
        variables in the new scope."""
        for key in kwargs:
            if key.startswith('_'):
                msg = "Cannot create dynamic binding for static var '{}'."
                raise RuntimeError(msg.format(key))
        return _Scope(self, kwargs)

    def update(self, env):
        """Update this environment with variables from another environment."""
        stack = env.__dict__['__stack']
        for scope in stack:
            for name,value in scope.items():
                setattr(self, name, value)

    def new(self, **kwargs):
        """Return a context manager that temporarily swaps the environment
        with a clean new environment. Useful for testing."""
        new = type(self)(**kwargs)
        return _Swapper(self, new)

    def copy(self, **kwargs):
        """Create a copy of an environment. Useful for testing."""
        new = type(self)()
        new.update(self)
        for key in kwargs:
            setattr(new, key, kwargs[key])
        return _Swapper(self, new)

    def __repr__(self):
        clsname = self.__class__.__name__
        stack = self.__dict__['__stack']
        header = '<{}(), <depth={}>'.format(clsname, len(stack))
        exc_stack = self.__dict__['__exc_stack']
        show_exc_stack = sys.exc_info() and exc_stack
        if show_exc_stack:
            header += ', <exc_depth={}>'.format(len(exc_stack))
        header += '>'
        lines = [header]
        lines.append('  Current Environment:')
        for name,value,depth in stack_vars(stack):
            if not name.startswith('_') or self.verbose:
                lines.append('    {}[{}]: {}'.format(name, depth, value))
        if show_exc_stack:
            lines.append('  Exception Environment:')
            for name,value,depth in stack_vars(exc_stack):
                if not name.startswith('_') or self.verbose:
                    lines.append('    {}[{}]: {}'.format(name, depth, value))
        lines.append('')
        res = '\n'.join(lines)
        return res


env = _Environment()
