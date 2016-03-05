"""
Automatically imports the two submodules used.
#
Written By: Matthew Stadelman
Date Written: 2016/02/26
Last Modifed: 2016/02/26
#
"""
#
import os
import re
import sys
#
# checking python version
if sys.version_info < (3,3):
    raise Exception('ApertureMapModelTools requires Python 3.3 or greater')
#
#
from .__core__ import *
from . import DataProcessing