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

import argparse


class ParseError(Exception):
    """Raised by ``ArgumentParser.error()`` to abort parsing."""


class ArgumentParser(argparse.ArgumentParser):
    """An ArgumentParser with two added features:

    * No formatting is done whatsoever. We get complete control over
      the output of the usage and help texts.
    * The function ``parse_args()`` will raise a ``ParseError`` exception
      instead of exiting. The exception will have a ``.namespace`` attribute
      that contains the parsed arguments so far.
    """

    def format_help(self):
        parts = [self.usage, self.description]
        return '\n'.join(parts)

    def format_usage(self):
        return self.usage

    def error(self, message):
        raise ParseError(message)

    def parse_args(self, args=None, namespace=None):
        if namespace is None:
            namespace = argparse.Namespace()
        try:
            super(ArgumentParser, self).parse_args(args, namespace)
        except ParseError as e:
            e.namespace = namespace
            raise
        return namespace
