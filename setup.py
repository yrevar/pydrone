from pydrone import __version__
VERSION = "%s.%s.%s" % __version__[0:3]

from setuptools import setup, Command, Extension
from setuptools.command.sdist import sdist
from shutil import rmtree
from stat import ST_MTIME
import os
import sys

try:
    import epydoc.cli as doc
except ImportError:
    doc = None

NAME = 'pydrone'
URL = 'https://github.com/alarconj/pydrone'
PACKAGE = 'pydrone'

CYTHON_MODULES = ['arvideo']


class GenerateDoc(Command):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        if not doc:
            raise ImportError('Epydoc is not available')
        rmtree('doc', ignore_errors=True)
        os.mkdir('doc')
        sys.argv = ['epydoc', '-v', '--name', NAME, '--url', URL, '-o', 'doc', PACKAGE]
        options, names = doc.parse_arguments()
        doc.main(options, names)


class CheckSdist(sdist):
    def initialize_options(self):
        sdist.initialize_options(self)
        self._pyxfiles = []
        for root, dirs, files in os.walk('.'):
            for f in files:
                if f.endswith('.pyx'):
                    self._pyxfiles.append(os.path.join(root, f)[2:])

    def run(self):
        for pyxfile in self._pyxfiles:
            cfile = pyxfile[:-3]+'c'
            assert os.path.isfile(cfile), 'C source file \'%s\' not found, run \'cython %s\' before \'sdist\'.' % (cfile, pyxfile)
            assert os.stat(cfile)[ST_MTIME] > os.stat(pyxfile)[ST_MTIME], 'C source file \'%s\' is out of date, run \'cython %s\' before \'sdist\'.' % (cfile, pyxfile)
        sdist.run(self)


setup(
    name = NAME,
    version = VERSION,
    license = 'MIT',
    description = 'Python API for the ARDrone.',
    author = 'Bastian Venthur',
    author_email = 'bastian.venthur@tu-berlin.de',
    url = URL,
    keywords = 'python api ardrone robotics',
    packages = [PACKAGE],
    test_suite = 'test_libardrone',
    cmdclass = {'doc': GenerateDoc, 'sdist': CheckSdist},
    ext_modules = [Extension('%s.%s' % (NAME, module), ['%s/%s.c' % (NAME, module)]) for module in CYTHON_MODULES],
)
