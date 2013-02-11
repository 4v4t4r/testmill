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


# These inflection functions are trivial and only work for regular nouns
# and verbs. Special cases can be added as and when needed.

def plural_noun(noun, count=2):
    """Takes a singular English noun ``noun`` and returns a plural version,
    depending on ``count``."""
    if count == 1:
        return noun
    else:
        return noun + 's'

def plural_verb(verb, count=2):
    """Return the plural conjugation of the English verb ``verb``, depending
    on ``count``."""
    if count == 1:
        if verb == 'was':
            return 'was'
        return verb + 's'
    else:
        if verb == 'was':
            return 'were'
        return verb
