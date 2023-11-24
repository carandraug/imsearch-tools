#!/usr/bin/env python

from hashlib import md5

import requests

from imsearchtools.engines import SearchClient


## API Configuration
#  --------------------------------------------

GOOGLE_API_ENTRY = "https://www.googleapis.com/customsearch/"
GOOGLE_API_FUNC = "v1"

## Search Class
#  --------------------------------------------


class GoogleAPISearch(requests.Session, SearchClient):
    """Wrapper class for Google Custom Search API (for images). For more details see:
    https://developers.google.com/custom-search/v1/overview/
    https://developers.google.com/custom-search/json-api/v1/reference/cse/list

    This uses a Google Programmable Search Engine and Google's Custom
    Search JSON API .  These are two things that need to be setup
    separately:

    1. The Programmable Search Engine needs to be setup first and
       controls what is searched (restricted list of websites or whole
       web, whether safe search is enabled, language, etc).  From this
       we need the search engine ID (sometimes called API context).

    2. The Custom Search JSON API is the method to search on that
       search engine.  An API key is required to search it with this
       class.

    Args:
        api_key: API key for custom Search JSON API.
        search_engine_id: the ID for the programmable Search Engine to
            use.

    """

    def __init__(
        self,
        api_key: str,
        search_engine_id: str,
        async_query=True,
        timeout=5.0,
        **kwargs,
    ):
        super().__init__()
        self.api_key = api_key
        self.search_engine_id = search_engine_id

        self.headers.update(kwargs)
        self.timeout = timeout

        self._results_per_req = 10
        self._supported_sizes_map = {
            "small": "medium",
            "medium": "large",
            "large": "xxlarge",
        }
        self._supported_styles_map = {
            "photo": "photo",
            "clipart": "clipart",
            "lineart": "lineart",
            "face": "face",
            "news": "news",
        }
        self.async_query = async_query

    def _fetch_results_from_offset(
        self, query, result_offset, aux_params={}, headers={}, num_results=-1
    ):
        if num_results == -1:
            num_results = self._results_per_req
        try:
            req_result_count = min(
                self._results_per_req, num_results - result_offset
            )

            # add query position to auxilary parameters
            aux_params["q"] = query
            aux_params["start"] = result_offset + 1
            aux_params["num"] = req_result_count

            resp = self.get(
                GOOGLE_API_ENTRY + GOOGLE_API_FUNC,
                params=aux_params,
                headers=headers,
            )
            resp.raise_for_status()

            # extract list of results from response
            result_dict = resp.json()

            return result_dict["items"][: (num_results - result_offset)]

        except requests.exceptions.RequestException:
            return []

    def __google_results_to_results(self, results):
        return [
            {
                "url": item["link"],
                "image_id": md5(item["link"].encode("utf-8")).hexdigest(),
                "title": item["title"],
            }
            for item in results
        ]

    def query(self, query, size="medium", style="photo", num_results=100):
        # check input
        if num_results > 100:
            raise ValueError(
                "Google API currently allows for a maximum of 100 results to be returend"
            )

        # prepare query parameters
        size = self._size_to_native_size(size)
        style = self._style_to_native_style(style)

        # prepare auxilary parameter list
        aux_params = {
            "cx": self.search_engine_id,
            "key": self.api_key,
            "searchType": "image",
        }
        if size:
            aux_params["imgSize"] = size
        if style:
            aux_params["imgType"] = style

        # do request
        results = self._fetch_results(
            query, num_results, aux_params=aux_params
        )

        return self.__google_results_to_results(results)
