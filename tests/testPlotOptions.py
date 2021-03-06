# -*- coding: utf-8 -*-
"""
Created on August 14, 2020

@author: joseph-hellerstein
"""

from SBstoat._plotOptions import PlotOptions

import unittest
import matplotlib
import matplotlib.pyplot as plt


IGNORE_TEST = False
IS_PLOT = False
TITLE = "A Title"
FONTSIZE = "30"
       
 
class TestPlotOptions(unittest.TestCase):

    def setUp(self):
        self.options = PlotOptions()

    def testSetDict(self):
        if IGNORE_TEST:
            return
        FIGSIZE = "figsize"
        FIGSIZE_VALUE = (12, 20)
        DUMMY = "dummy"
        DUMMY_VALUE = "value"
        dct = {FIGSIZE: FIGSIZE_VALUE}
        self.options.setDict(dct)
        self.assertEqual(FIGSIZE_VALUE, self.options.figsize)
        #
        dct[DUMMY] = DUMMY_VALUE
        with self.assertRaises(ValueError):
            self.options.setDict(dct)


if __name__ == '__main__':
    #matplotlib.use('TkAgg')
    unittest.main()
