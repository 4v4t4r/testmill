#
# Sphinx extension providing an 'autocmd' directive

import os
import sys
from sphinx.util.compat import Directive
from docutils import nodes

def libdir():
    path = os.path.abspath(__file__)
    for i in range(2):
        path, _ = os.path.split(path)
    libdir = os.path.join(path, 'lib')
    return libdir

sys.path.insert(0, libdir())

from testmill import main, argparse


class AutoCmdDirective(Directive):
    
    has_content = True

    def run(self):
        name = self.content[0]
        func, add_args = main.subcommands[name]
        parser = argparse.ArgumentParser()
        add_args(parser)
        usage = parser.usage
        description = parser.description.splitlines()
        path = 'command:{0}'.format(name)
        self.state_machine.insert_input(description, path)
        return [nodes.literal_block(text=usage)]


def setup(app):
    app.add_directive('autocmd', AutoCmdDirective)
