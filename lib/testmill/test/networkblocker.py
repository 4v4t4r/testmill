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

import sys
from testmill.test import sudo


def have_blocker():
    return sys.platform in ('darwin', 'linux2')


class block_ip(object):
    """Context manager that block IP traffic to a certain IP."""

    def __init__(self, ipaddr):
        self.ipaddr = ipaddr

    def __enter__(self):
        # Actually we DROP the return traffic rather than the ougoing
        # traffic. Dropping the outgoing traffic has different issues on
        # different platforms. For example a local ICMP unreachable may
        # be generated or existing connections may not be impacted.
        if sys.platform == 'darwin':
            command = 'ipfw -q add 2000 drop tcp from {} to any' \
                        .format(self.ipaddr)
        elif sys.platform == 'linux2':
            command = 'iptables -I INPUT 1 -s {} -j DROP' \
                        .format(self.ipaddr)
        sudo.run_with_sudo(command.split())

    def __exit__(self, *exc):
        if sys.platform == 'darwin':
            command = 'ipfw -q del 2000'
        elif sys.platform == 'linux2':
            command = 'iptables -D INPUT 1'
        sudo.run_with_sudo(command.split()) 
