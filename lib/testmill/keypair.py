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

import os
import stat
import socket
import subprocess

from testmill import util, console, error, util
from testmill.state import env


def load_keypair():
    """Try to load a keypair that exists in ~/.ravello."""
    cfgdir = util.get_config_dir()
    privname = os.path.join(cfgdir, 'id_ravello')
    try:
        st = os.stat(privname)
    except OSError:
        return
    if not stat.S_ISREG(st.st_mode):
        error.raise_error("Private key {0} is not a regular file.", pivname)
    pubname = privname + '.pub'
    try:
        st = os.stat(pubname)
    except OSError:
        st = None
    if st is None:
        error.raise_error("Public key {0} does not exist.", pubname)
    elif not stat.S_ISREG(st.st_mode):
        error.raise_error("Public key {0} is not a regular file.", pubname)
    with file(pubname) as fin:
        pubkey = fin.read()
    keyparts = pubkey.strip().split()
    pubkeys = env.api.get_pubkeys()
    for pubkey in pubkeys:
        if pubkey['name'] == keyparts[2]:
            env.public_key = pubkey
            env.private_key_file = privname
            return pubkey


def create_keypair():
    """Create a new keypair and upload it to Ravello."""
    cfgdir = util.get_config_dir()
    privname = os.path.join(cfgdir, 'id_ravello')
    pubname = privname + '.pub'
    keyname = 'ravello@%s' % socket.gethostname()
    # Prefer to generate the key locallly with ssh-keygen because
    # that gives us more privacy. If ssh-keygen is not available, ask
    # for a key through the API.
    sshkeygen = util.which('ssh-keygen')
    if sshkeygen:
        try:
            console.info("Generating keypair using 'ssh-keygen'...")
            subprocess.call(['ssh-keygen', '-q', '-t', 'rsa', '-C', keyname,
                             '-b', '2048', '-N', '', '-f', privname])
        except subprocess.CalledProcessError as e:
            error.raise_error('ssh-keygen returned with error status {0}',
                              e.returncode)
        with file(pubname) as fin:
            pubkey = fin.read()
        keyparts = pubkey.strip().split()
    else:
        keyname = 'ravello@api-generated'
        console.info('Requesting a new keypair via the API...')
        keypair = env.api.create_keypair()
        with file(privname, 'w') as fout:
            fout.write(keypair['privateKey'])
        with file(pubname, 'w') as fout:
            fout.write(keypair['publicKey'].rstrip())
            fout.write(' {0} (generated remotely)\n'.format(keyname))
        pubkey = keypair['publicKey'].rstrip()
        keyparts = pubkey.split()
        keyparts[2:] = [keyname]
    # Create the pubkey in the API under a unique name
    pubkeys = env.api.get_pubkeys()
    keyname = util.get_unused_name(keyname, pubkeys)
    keyparts[2] = keyname
    keydata = '{0} {1} {2}\n'.format(*keyparts)
    pubkey = {'name': keyname}
    pubkey['publicKey'] = keydata
    pubkey = env.api.create_pubkey(pubkey)
    with file(pubname, 'w') as fout:
        fout.write(keydata)
    env.public_key = pubkey
    env.private_key_file = privname
    return pubkey


def default_keypair():
    """Check if we have a keypair. If not, create it."""
    pubkey = load_keypair()
    if not pubkey:
        pubkey = create_keypair()
    return pubkey
