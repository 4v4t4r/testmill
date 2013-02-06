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

# Some standard exit codes from sysexits.h and bash.

EX_OK = 0
EX_USAGE = 64
EX_DATAERR = 65
EX_NOINPUT = 66
EX_SOFTWARE = 70
EX_INTERRUPTED = 130


class ProgramError(RuntimeError):

    def __init__(self, message, *args, **kwds):
        super(ProgramError, self).__init__(message, *args)
        for key in kwds:
            setattr(self, key, kwds[key])

    def __str__(self):
        return self.args[0]


def raise_error(message, *args, **kwds):
    """Raise an exception. The exception is normally caught in the main
    function and will exit TestMill.
    """
    if args or kwds:
        message = message.format(*args, **kwds)
    raise ProgramError(message, *args, **kwds)

error = raise_error


def exit(status=EX_SOFTWARE):
    raise SystemExit(status)
