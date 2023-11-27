#!/usr/bin/env python

import os
import sys
import time

from imsearchtools.engines.bing_api_v5 import BingAPISearchV5
from imsearchtools.engines.flickr_api import FlickrAPISearch
from imsearchtools.engines.google_api import GoogleAPISearch
from imsearchtools.engines.google_web import GoogleWebSearch
from imsearchtools.utils import result_page_gen


if len(sys.argv) < 2:
    test_query_str = "car"
else:
    test_query_str = sys.argv[1]

outdir = os.path.join(os.getcwd(), "demos")
if not os.path.isdir(outdir):
    os.makedirs(outdir)

# Note that actually testing these requires defining the corresponding
# API keys (see variables below).
test_bing_api_v5 = True
test_google_api = True
test_google_web = True
test_flickr_api = True

bing_api_v5_key = ""
google_search_engine_id = ""
google_api_key = ""
flickr_api_key = ""

num_results = 100

display_results = True

all_results = []
all_generator_names = []

if test_bing_api_v5:
    if not bing_api_v5_key:
        print("Bing API Key not specified - this is likely to fail")
    bing_api_searcher = BingAPISearchV5(bing_api_v5_key)
    print("Executing Bing API Search V5...")
    t = time.time()
    bing_api_results = bing_api_searcher.query(test_query_str)
    bing_api_timing = time.time() - t
    print(
        "Retrieved %d results in %f seconds"
        % (len(bing_api_results), bing_api_timing)
    )

    result_page_gen.gen_results_page(
        bing_api_results,
        "BingAPISearchV5()",
        os.path.join(outdir, "bing_api_v5_results.html"),
        show_in_browser=False,
    )

    all_results.append(bing_api_results)
    all_generator_names.append("BingAPISearchV5()")

if test_google_api:
    if not google_api_key:
        print("Google API Key not specified - this is likely to fail")
    if not google_search_engine_id:
        print("Google Search engine ID not specified - this is likely to fail")
    google_api_searcher = GoogleAPISearch(
        google_api_key, google_search_engine_id
    )
    print("Executing Google API Search (Custom Search)...")
    t = time.time()
    google_api_results = google_api_searcher.query(
        test_query_str, num_results=num_results
    )
    google_api_timing = time.time() - t
    print(
        "Retrieved %d results in %f seconds"
        % (len(google_api_results), google_api_timing)
    )

    result_page_gen.gen_results_page(
        google_api_results,
        "GoogleAPISearch()",
        os.path.join(outdir, "google_api_results.html"),
        show_in_browser=False,
    )

    all_results.append(google_api_results)
    all_generator_names.append("GoogleAPISearch()")

if test_google_web:
    google_web_searcher = GoogleWebSearch()
    print("Executing Google Web Search...")
    t = time.time()
    google_web_results = google_web_searcher.query(
        test_query_str, num_results=num_results
    )
    google_web_timing = time.time() - t
    print(
        "Retrieved %d results in %f seconds"
        % (len(google_web_results), google_web_timing)
    )

    result_page_gen.gen_results_page(
        google_web_results,
        "GoogleWebSearch()",
        os.path.join(outdir, "google_web_results.html"),
        show_in_browser=False,
    )

    all_results.append(google_web_results)
    all_generator_names.append("GoogleWebSearch()")


if test_flickr_api:
    if not flickr_api_key:
        print("Flickr API key not specified - this is likely to fail")
    flickr_api_searcher = FlickrAPISearch(flickr_api_key)
    print("Executing Flickr API Search...")
    t = time.time()
    flickr_api_results = flickr_api_searcher.query(
        test_query_str, num_results=num_results
    )
    flickr_api_timing = time.time() - t
    print(
        "Retrieved %d results in %f seconds"
        % (len(flickr_api_results), flickr_api_timing)
    )

    result_page_gen.gen_results_page(
        flickr_api_results,
        "FlickrApiSearch()",
        os.path.join(outdir, "flickr_api_results.html"),
        show_in_browser=False,
    )

    all_results.append(flickr_api_results)
    all_generator_names.append("FlickrAPISearch()")

if display_results:
    result_page_gen.combine_results_pages(
        all_results,
        all_generator_names,
        os.path.join(outdir, "combined_results.html"),
    )
