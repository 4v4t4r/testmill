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

import textwrap
import time
from . import main


class PsCommand(main.SubCommand):

    name = 'ps'
    usage = textwrap.dedent("""\
            usage: ravtest [OPTION]... ps
            """)
    description = textwrap.dedent("""\
            Show your running applications in Ravello.
            """)

    def run(self, args):
        """The "ravello ps" command."""
        apps = self.api.get_applications()
        self.write('Currently published applications:')
        for app in sorted(apps, key=lambda x: x['name']):
            name = app['name']
            app = self.api.get_application(app['id'])
            cloud = app['cloud']
            region = app['regionName']
            started = total = 0
            for stat in app.get('cloudVmsStatusCounters'):
                if stat['status'] == 'STARTED':
                    started += stat['cloudWithDesignVmCounter']
                total += stat['cloudWithDesignVmCounter']
            if started:
                tm = time.localtime(app['publishStartTime'] / 1000)
                starttime = time.strftime('%Y/%m/%d %H:%M:%S', tm)
            else:
                starttime = ''
            self.write('== {0}'.format(name))
            self.write('  {0}/{1} VMs running'.format(started, total))
            self.write('  published to {0}/{1}'.format(cloud, region))
            if started:
                self.write('  started: {0}'.format(starttime))
            self.write('')
