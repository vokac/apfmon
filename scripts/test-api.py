#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import random
import requests
import unittest


APFMONURL = os.environ.get('APFMON_URL', 'http://localhost:80/api/')

def apfmon(*suffix):
    """Returns url for APFMON resource."""
    return APFMONURL + '/'.join(suffix)

class APFmonTestCase(unittest.TestCase):

    _multiprocess_can_split_ = True

    def setUp(self):
        """Create a few jobs, clearly this needs to work too."""
        self.jobs = []
        for j in range(3):
            cid = str(random.randint(1,10000))
            job = {
                  'cid'     : 'dev' + cid,
                  'nick'    : 'dev-nick',
                  'factory' : 'dev-unittest',
                  'label'   : 'dev-label',
                }
            self.jobs.append(job)
        payload = json.dumps(self.jobs)
        url = apfmon('jobs')
        r = requests.put(url, data=payload)

    def tearDown(self):
        """Teardown."""
        for job in self.jobs:
            jid = ':'.join((job['factory'], job['cid']))
            url = apfmon('jobs',jid)
            r = requests.delete(url)
        del self.jobs

    def test_assertion(self):
        assert 1

#    def test_HTTP_200_OK_HEAD(self):
#        r = requests.head(apfmon('get'))
#        self.assertEqual(r.status_code, 200)

#    def test_JOBS_200_OK_PUT(self):
#        payload = json.dumps(self.jobs)
#        url = apfmon('jobs')
#        r = requests.put(url, data=payload)
#        self.assertEqual(r.status_code, 200)
        
    def test_JOBS_200_OK_GET(self):
#        # create jobs again
#        payload = json.dumps(self.jobs)
#        url = apfmon('jobs')
#        r = requests.put(url, data=payload)

        for job in self.jobs:
            jid = ':'.join((job['factory'], job['cid']))
            url = apfmon('jobs',jid)
            r = requests.put(url)
            self.assertEqual(r.status_code, 200)

    def test_JOBS_200_OK_GET_WITH_PARAMS(self):
        """GET list of jobs refined by query params /jobs"""
        for job in self.jobs:
            url = apfmon('jobs')
            payload = {
                    'factory' : 'dev-unittest',
                    'state'   : 'created',
                    }
            r = requests.get(url, params=payload)
            self.assertEqual(r.status_code, 200)

    def test_FACTORIES_200_OK_GET_ALL(self):
        """GET a list of all factories /factories"""
        url = apfmon('factories')
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)

    def test_FACTORIES_200_OK_GET_SINGLE(self):
        """GET a single factory"""
        url = apfmon('factories', 'dev-unittest')
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
        
    def test_FACTORIES_404_NOTFOUND_GET_NONEXISTENT(self):
        """GET a single factory which does not exist"""
        url = apfmon('factories', 'dev-notfound')
        r = requests.get(url)
        self.assertEqual(r.status_code, 404)


    def test_FACTORIES_201_CREATED_PUT_NEW_FACTORY(self):
        """PUT a new factory"""
        factory = '-'.join(('new',str(random.randint(100,999))))
        url = apfmon('factories',factory)
        f = {
             'url'     : 'http://localhost/',
             'email'   : 'p.love@lancaster.ac.uk',
             'version' : '0.0.1',
            }
        payload = json.dumps(f)
        r = requests.put(url, data=payload)
        self.assertEqual(r.status_code, 201)

    def test_JOBS_200_OK_UPDATE_STATE(self):
        """POST update the job status via query params"""
        for job in self.jobs:
            jid = ':'.join((job['factory'],job['cid']))
            url = apfmon('jobs',jid)
            payload = {'state' : 'running'}
            r = requests.post(url, data=payload)
            self.assertEqual(r.status_code, 200)

    def test_JOBS_200_OK_UPDATE_INVALID_STATE(self):
        """POST update the job status via query params"""
        for job in self.jobs:
            jid = ':'.join((job['factory'],job['cid']))
            url = apfmon('jobs',jid)
            payload = {'state' : 'exiting'}
            r = requests.post(url, data=payload)
            self.assertEqual(r.status_code, 400)

if __name__ == '__main__':
    unittest.main()
