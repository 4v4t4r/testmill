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
import yaml


class MockRavelloClient(object):

    def __init__(self, **kwargs):
        testdir, _ = os.path.split(os.path.abspath(__file__))
        fname = os.path.join(testdir, 'mockdata.yml')
        self.mockdata = yaml.load(fname)

    def close(self):
        pass

    def get_image(self, id):
        for img in self.get_images():
            if img.get('id') == id:
                return img

    def get_images(self):
        return self.mockdata.get('images', [])

    def get_blueprint(self, id):
        for bp in self.get_blueprints():
            if bp.get('id') == id:
                return bp

    def get_blueprints(self):
        return self.mockdata.get('blueprints', [])
