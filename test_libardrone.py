"""\
Copyright (c) 2011 Bastian Venthur

The license and distribution terms for this file may be
found in the file LICENSE in this distribution.
"""


import unittest

from pydrone import libardrone

class LibardroneTestCase(unittest.TestCase):
    def test_f2i(self):
        self.assertEqual(libardrone.f2i(-0.8,), -1085485875)

if __name__ == "__main__":
    unittest.main()
