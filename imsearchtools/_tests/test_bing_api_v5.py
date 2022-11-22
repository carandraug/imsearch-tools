import os
import re
import sys

import requests

from imsearchtools.engines.bing_api_v5 import BingAPISearchV5


class TestBingAPI(object):
    def setup(self):
        self._gws = BingAPISearchV5(False)
        self._q = "polka dots"

    def test_query(self):
        res = self._gws.query(self._q, num_results=10)
        print(res)

    def test_images_returned(self):
        res = self._gws.query(self._q, num_results=100)
        assert len(res) == 100


test = TestBingAPI()
test.setup()
test.test_images_returned()
