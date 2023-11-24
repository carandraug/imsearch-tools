#!/usr/bin/env python

import argparse
import logging
import os
import sys

from flask import Flask, Response, json, request
from gevent.pywsgi import WSGIServer

from imsearchtools.engines.bing_api_v5 import BingAPISearchV5
from imsearchtools.engines.flickr_api import FlickrAPISearch
from imsearchtools.engines.google_api import GoogleAPISearch
from imsearchtools.engines.google_old_api import GoogleOldAPISearch
from imsearchtools.engines.google_web import GoogleWebSearch
from imsearchtools.postproc_modules import module_finder
from imsearchtools.process import (
    callback_handler,
    image_getter,
    image_processor,
)


# logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=logging.DEBUG)
logging.basicConfig(
    format="%(asctime)s %(levelname)s:%(message)s", level=logging.INFO
)


DEFAULT_SERVER_PORT = 8157
SUPPORTED_ENGINES = ["bing_api", "google_api", "google_web", "flickr_api"]

zmq_context = (
    None  # used to store zmq context created by init_zmq_context function
)

app = Flask(__name__)
app.debug = True


def imsearch_query(query, engine, query_params, query_timeout=-1.0):
    # prepare input arguments for searcher initialization if non-default
    searcher_args = dict()
    if query_timeout > 0.0:
        searcher_args["timeout"] = query_timeout
    # initialize searcher
    if engine == "bing_api":
        searcher = BingAPISearchV5(**searcher_args)
    elif engine == "google_old_api":
        searcher = GoogleOldAPISearch(**searcher_args)
    elif engine == "google_api":
        searcher = GoogleAPISearch(**searcher_args)
    elif engine == "google_web":
        searcher = GoogleWebSearch(**searcher_args)
    elif engine == "flickr_api":
        searcher = FlickrAPISearch(**searcher_args)
    else:
        raise ValueError("Unknown query engine")
    # execute the query
    return searcher.query(query, **query_params)


def imsearch_download_to_static(
    query_res_list,
    postproc_module=None,
    postproc_extra_prms=None,
    custom_local_path=None,
    imgetter_params=None,
    zmq_context=None,
):
    # prepare extra parameters if required
    ig_params = dict()
    if imgetter_params:
        if (
            "improc_timeout" in imgetter_params
            and imgetter_params["improc_timeout"] > 0.0
        ):
            ig_params["timeout"] = imgetter_params["improc_timeout"]
        if (
            "per_image_timeout" in imgetter_params
            and imgetter_params["per_image_timeout"] > 0.0
        ):
            ig_params["image_timeout"] = imgetter_params["per_image_timeout"]
        do_width_resize = (
            "resize_width" in imgetter_params
            and imgetter_params["resize_width"] > 0
        )
        do_height_resize = (
            "resize_height" in imgetter_params
            and imgetter_params["resize_height"] > 0
        )
        if do_width_resize or do_height_resize:
            improc_settings = image_processor.ImageProcessorSettings()
            if do_width_resize:
                improc_settings.conversion["max_width"] = imgetter_params[
                    "resize_width"
                ]
            if do_height_resize:
                improc_settings.conversion["max_height"] = imgetter_params[
                    "resize_height"
                ]
            ig_params["opts"] = improc_settings

    imgetter = image_getter.ImageGetter(**ig_params)

    if not custom_local_path:
        outdir = os.path.join(app.config["base-dir"], "static")
    else:
        outdir = custom_local_path
    if not os.path.isdir(outdir):
        os.makedirs(outdir)

    # add zmq context and socket as extra parameter if required
    if type(postproc_extra_prms) is not dict:
        postproc_extra_prms = {}

    if zmq_context:
        postproc_extra_prms["zmq_context"] = zmq_context
    # *** pre-creating a connection seems to cause the gevent threads to hang on joining so disable for now ***
    # if 'zmq_impath_return_ch' in postproc_extra_prms and 'zmq_context' in postproc_extra_prms
    #    import zmq
    #    context = postproc_extra_prms['zmq_context']
    #    postproc_extra_prms['zmq_impath_return_sock'] = context.socket(zmq.REQ)
    #    postproc_extra_prms['zmq_impath_return_sock'].connect(postproc_extra_prms['zmq_impath_return_ch'])

    # if a postprocessing module is defined, find the callback function
    # of the module
    if postproc_module:
        callback_func = module_finder.get_module_callback(postproc_module)
        if postproc_extra_prms:
            return imgetter.process_urls(
                query_res_list,
                outdir,
                callback_func,
                completion_extra_prms=postproc_extra_prms,
            )

        return imgetter.process_urls(query_res_list, outdir, callback_func)

    return imgetter.process_urls(query_res_list, outdir)


def make_url_dfiles_list(dfiles_list, base_dir):
    # recast local fs image paths as server paths using hostname from request
    for dfile_ifo in dfiles_list:
        dfile_ifo["orig_fn"] = (
            "http://"
            + request.host
            + dfile_ifo["orig_fn"].replace(base_dir, "")
        )
        dfile_ifo["thumb_fn"] = (
            "http://"
            + request.host
            + dfile_ifo["thumb_fn"].replace(base_dir, "")
        )
        dfile_ifo["clean_fn"] = (
            "http://"
            + request.host
            + dfile_ifo["clean_fn"].replace(base_dir, "")
        )
    return dfiles_list


def get_postproc_modules():
    return module_finder.get_module_list()


def test_callback():
    cbhandler = callback_handler.CallbackHandler(test_func, 100, 50)
    for i in range(0, 100):
        cbhandler.run_callback()
    print("Done launching callbacks!")
    cbhandler.join()
    print("Done joining callbacks")


def test_func():
    import time

    time.sleep(5.0)


@app.route("/")
def index():
    return "imsearch HTTP service is running"


@app.route("/callback_test")
def callback_test():
    test_callback()
    return "Done!"


@app.route("/query")
def query():
    # parse GET args
    query_text = request.args["q"]
    engine = request.args.get("engine", "google_web")

    query_params = dict()
    for param_nm in ["size", "style"]:
        if param_nm in request.args:
            query_params[param_nm] = request.args[param_nm]
    if "num_results" in request.args:
        query_params["num_results"] = int(request.args["num_results"])

    # execute query
    query_res_list = imsearch_query(query_text, engine, query_params)
    return Response(json.dumps(query_res_list), mimetype="application/json")


@app.route("/download", methods=["POST"])
def download():
    # parse POST data
    query_res_list = request.json
    if not query_res_list:
        raise ValueError(
            "Input must be 'application/json' encoded list of urls"
        )
    # download images
    dfiles_list = imsearch_download_to_static(query_res_list)
    # convert pathnames to URL paths
    url_dfiles_list = make_url_dfiles_list(dfiles_list, app.config["base-dir"])

    return Response(json.dumps(url_dfiles_list), mimetype="application/json")


@app.route("/get_engine_list")
def get_engine_list():
    return json.dumps(SUPPORTED_ENGINES)


@app.route("/get_postproc_module_list")
def get_postproc_module_list():
    return json.dumps(get_postproc_modules())


@app.route("/init_zmq_context")
def init_zmq_context():
    global zmq_context
    if not zmq_context:
        import zmq

        zmq_context = zmq.Context()
    return "Success"


@app.route("/exec_pipeline", methods=["POST"])
def exec_pipeline():
    # parse POST form args
    query_text = request.form["q"]
    engine = request.form.get("engine", "google_web")
    postproc_module = request.form.get(
        "postproc_module", None
    )  # default to no postproc module
    postproc_extra_prms = request.form.get("postproc_extra_prms", None)
    if postproc_extra_prms:
        postproc_extra_prms = json.loads(postproc_extra_prms)
    custom_local_path = request.form.get("custom_local_path", None)
    # < default to returning list only if not using postproc module >
    return_dfiles_list = request.form.get(
        "return_dfiles_list", (postproc_module is None)
    )
    return_dfiles_list = int(return_dfiles_list) == 1

    # prepare query params
    query_timeout = request.form.get("query_timeout", -1.0)
    query_timeout = float(query_timeout)
    query_params = dict()
    for param_nm in ["size", "style"]:
        if param_nm in request.form:
            query_params[param_nm] = request.form[param_nm]
    if "num_results" in request.form:
        query_params["num_results"] = int(request.form["num_results"])
    # execute query
    query_res_list = imsearch_query(
        query_text, engine, query_params, query_timeout
    )
    print(
        "Query for %s completed: %d results retrieved"
        % (query_text, len(query_res_list))
    )
    # query_res_list = query_res_list[:5] # DEBUG CODE
    # prepare download params
    imgetter_params = dict()
    for param_nm in ["improc_timeout", "per_image_timeout"]:
        if param_nm in request.form:
            imgetter_params[param_nm] = float(request.form[param_nm])
    for param_nm in ["resize_width", "resize_height"]:
        if param_nm in request.form:
            imgetter_params[param_nm] = int(request.form[param_nm])
    # download images
    print(
        "Downloading for %s started: %d sec improc_timeout, %d sec per_image_timeout"
        % (
            query_text,
            imgetter_params["improc_timeout"]
            if imgetter_params["improc_timeout"]
            else -1,
            imgetter_params["per_image_timeout"]
            if imgetter_params["per_image_timeout"]
            else -1,
        )
    )
    dfiles_list = imsearch_download_to_static(
        query_res_list,
        postproc_module,
        postproc_extra_prms,
        custom_local_path,
        imgetter_params,
        zmq_context,
    )
    print(
        "Downloading for %s completed: %d images retrieved"
        % (query_text, len(dfiles_list))
    )
    # convert pathnames to URL paths (if not running locally and specifying
    # a custom path)
    if not custom_local_path:
        dfiles_list = make_url_dfiles_list(dfiles_list, app.config["base-dir"])

    if return_dfiles_list:
        return Response(json.dumps(dfiles_list), mimetype="application/json")

    return "DONE"


if __name__ == "__main__":
    argv_parser = argparse.ArgumentParser()
    argv_parser.add_argument(
        "--base-dir",
        default=os.getcwd(),
        help="save results relative to this directory (default: current directory)",
    )
    argv_parser.add_argument(
        "port",
        type=int,
        default=DEFAULT_SERVER_PORT,
        nargs="?",
        help="bind to this port (default: %(default)s)",
    )
    args = argv_parser.parse_args(sys.argv[1:])

    app.config["base-dir"] = args.base_dir

    print("Starting imsearch_http_service on port", args.port)
    http_server = WSGIServer(("", args.port), app)
    http_server.serve_forever()
