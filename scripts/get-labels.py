#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import random
import requests
import unittest


APFMONURL = os.environ.get('APFMON_URL', 'http://localhost:8000/api/')

def apfmon(*suffix):
    """Returns url for APFMON resource."""
    return APFMONURL + '/'.join(suffix)

class APFmonTestCase(unittest.TestCase):

    _multiprocess_can_split_ = True

    def test_LABELS_200_OK_GET_WITH_PARAMS(self):
        """GET labels using parameters"""
        url = apfmon('labels')
        r = requests.get(url)
        payload = {
                }
        r = requests.get(url, params=payload)
        print r.text
        self.assertEqual(r.status_code, 200)
        
if __name__ == '__main__':
    unittest.main()
