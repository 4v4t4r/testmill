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

import os
import re
import copy
import stat
import textwrap
import mock

from testmill.test import *
from testmill.test.fileops import *
from testmill import versioncontrol
from testmill.versioncontrol import *


class TestVersionControl(UnitTestSuite):
    """Test suite for the testmill.versioncontrol module."""

    # walk_repository()

    def create_repo(self):
        os.chdir(testenv.tempdir)
        with mkdir('dir1'):
            with mkdir('sub1'):
                touch('foo')
                touch('bar')
            with mkdir('sub2'):
                touch('baz')
        with mkdir('dir2'):
            with mkdir('sub2'):
                touch('foo')
                touch('qux')
            with mkdir('sub3'):
                touch('quux')

    def test_walk_repository(self):
        self.create_repo()
        gen = versioncontrol.walk_repository('.', repotype=None)
        elems = list(gen)
        assert len(elems) == 12
        join = os.path.join
        assert 'dir1' in elems
        assert join('dir1', 'sub1') in elems
        assert join('dir1', 'sub1', 'foo') in elems
        assert join('dir1', 'sub1', 'bar') in elems
        assert join('dir1', 'sub2') in elems
        assert join('dir1', 'sub2', 'baz') in elems
        assert 'dir2' in elems
        assert join('dir2', 'sub2') in elems
        assert join('dir2', 'sub2', 'foo') in elems
        assert join('dir2', 'sub2', 'qux') in elems
        assert join('dir2', 'sub3') in elems
        assert join('dir2', 'sub3', 'quux') in elems

    # Git specific tests

    # parse_gitignore()

    gitignore = text("""\
            foo
            foo*
            foo/bar
            foo*/bar
            foo/*/bar
            bar/
            !foo
            \!foo
            #comment

            \#comment
            """)

    def test_parse_gitignore_string(self):
        parsed = versioncontrol.parse_gitignore(self.gitignore)
        assert len(parsed) == 9
        for i in range(len(parsed)):
            assert len(parsed[i]) == 2
            assert isinstance(parsed[i][0], list)
            for pat in parsed[i][0]:
                assert hasattr(pat, 'match')
            assert isinstance(parsed[i][1], int)

    def test_parse_gitignore_stream(self):
        touch('.gitignore', self.gitignore)
        with file('.gitignore') as fin:
            parsed = versioncontrol.parse_gitignore(fin)
        assert len(parsed) == 9

    def test_parse_gitignore_patterns(self):
        with mock.patch('re.compile', lambda s: s):
            with mock.patch('fnmatch.translate', lambda s: s):
                parsed = versioncontrol.parse_gitignore(self.gitignore)
        assert parsed[0] == (['foo'], 0)
        assert parsed[1] == (['foo*'], 0)
        assert parsed[2] == (['foo', 'bar'], 0)
        assert parsed[3] == (['foo*', 'bar'], 0)
        assert parsed[4] == (['foo', '*', 'bar'], 0)
        assert parsed[5] == (['bar'], versioncontrol.MATCH_END_WITH_DIRECTORY)
        assert parsed[6] == (['foo'], versioncontrol.MATCH_INVERSE)
        assert parsed[7] == (['!foo'], 0)
        assert parsed[8] == (['#comment'], 0)

    # match_gitignore()

    def test_match_gitignore_types(self):
        path = [('foo', None, stat.S_IFREG)]
        assert versioncontrol.match_gitignore(path) == INCLUDE
        path = [('foo', [([re.compile('foo')], 0)], stat.S_IFREG)]
        assert versioncontrol.match_gitignore(path) == EXCLUDE

    def test_match_gitignore_single(self):
        path = [('foo', [([re.compile('.*')], 0)], stat.S_IFREG)]
        assert versioncontrol.match_gitignore(path)
        path = [('fo', [([re.compile('foo.*')], 0)], stat.S_IFREG)]
        assert not versioncontrol.match_gitignore(path)

    def test_match_gitignore_multiple(self):
        path = [('foo', None, False), ('bar', None, stat.S_IFREG)]
        assert not versioncontrol.match_gitignore(path)
        path = [('foo', None, True), ('bar', None, stat.S_IFREG)]
        assert versioncontrol.match_gitignore(path)
        path = [('foo', [([re.compile('bar')], 0)], False),
                    ('bar', None, stat.S_IFREG)]
        assert versioncontrol.match_gitignore(path)

    def test_match_gitignore_inverse(self):
        path = [('foo', [([re.compile('bar')], 0)], False),
                    ('bar', None, stat.S_IFREG)]
        assert versioncontrol.match_gitignore(path)
        path = [('foo', [([re.compile('bar')], versioncontrol.MATCH_INVERSE)], True),
                    ('bar', None, stat.S_IFREG)]
        assert not versioncontrol.match_gitignore(path)

    def test_match_gitignore_end_with_directory(self):
        path = [('foo', [([re.compile('bar')],
                            versioncontrol.MATCH_END_WITH_DIRECTORY)], False),
                    ('bar', None, stat.S_IFREG)]
        assert not versioncontrol.match_gitignore(path)
        path = [('foo', [([re.compile('bar')],
                            versioncontrol.MATCH_END_WITH_DIRECTORY)], False),
                    ('bar', None, stat.S_IFDIR)]
        assert versioncontrol.match_gitignore(path)

    # walk_repository(type='git')

    def create_git_repo(self):
        self.create_repo()
        mkfile('.gitignore', text("""\
            foo
            sub2/
            sub3
            bar/
            dir2/*/baz
            """))
        with chdir('dir2'):
            mkfile('.gitignore', text("""\
                    !sub2
                    """))

    def test_walk_git_repository(self):
        self.create_git_repo()
        gen = versioncontrol.walk_repository('.', repotype='git')
        elems = list(gen)
        assert len(elems) == 8
        join = os.path.join
        assert '.gitignore' in elems
        assert 'dir1' in elems
        assert join('dir1', 'sub1') in elems
        assert join('dir1', 'sub1', 'bar') in elems
        assert 'dir2' in elems
        assert join('dir2', '.gitignore') in elems
        assert join('dir2', 'sub2') in elems
        assert join('dir2', 'sub2', 'qux') in elems
