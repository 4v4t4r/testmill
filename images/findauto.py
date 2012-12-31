#!/usr/bin/env python

import os
import sys

def split(name, sep='-.'):
    p = max(map(lambda s: name.rfind(s), sep))
    if p == -1:
        p = len(name)
    return name[:p], name[p:]

fname = sys.argv[1]
while True:
    fname, ext = split(fname)
    if not ext:
        break
    auto = '%s.auto' % fname
    if os.access(auto, os.R_OK):
        sys.stdout.write('-a %s\n' % auto)
        break
