#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Quickview the plain_text ORKL field"""

import sys
from pprint import pprint

with open(sys.argv[1]) as fp:
    data = fp.readlines()
    for line in data:
        data2 = line.split('\\n')
        data2 = list(filter(None, data2))
        pprint(data2)
