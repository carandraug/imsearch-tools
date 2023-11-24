#!/usr/bin/env python

import logging
import os
import socket

import zmq
from flask import json


TCP_TERMINATOR = "$$$"
SUCCESS_FIELD = "success"
TCP_TIMEOUT = 86400.00


_logger = logging.getLogger(__name__)


def callback_func(out_dict, extra_prms=None):
    # connect to VISOR backend service
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((extra_prms["backend_host"], extra_prms["backend_port"]))
    except socket.error as msg:
        _logger.error("VISOR FACES: Connect failed: %s", msg)
        raise socket.error

    sock.settimeout(TCP_TIMEOUT)

    # generate feature file path from image file path
    imfn = os.path.basename(out_dict["clean_fn"])
    (featfn, imext) = os.path.splitext(imfn)
    featfn += ".bin"
    featpath = os.path.join(extra_prms["featdir"], featfn)
    extra_params = dict()
    if "detector" in extra_prms:
        extra_params["detector"] = extra_prms["detector"]
    # construct VISOR backend function call
    func_in = dict(
        func=extra_prms["func"],
        query_id=extra_prms["query_id"],
        impath=out_dict["clean_fn"],
        featpath=featpath,
        from_dataset=0,
        extra_params=extra_params,
    )
    request = json.dumps(func_in)

    _logger.info("VISOR FACES: Request to VISOR backend: %s ", request)
    request = request + TCP_TERMINATOR

    # send request to VISOR backend
    sock.send(request.encode())

    response = ""
    while 1:
        try:
            data = sock.recv(1024)
            data = data.decode()
            response += data
            if len(response) >= len(TCP_TERMINATOR):
                if response[-len(TCP_TERMINATOR) :] == TCP_TERMINATOR:
                    break
        except socket.timeout:
            _logger.error("VISOR FACES: Socket timeout")
            sock.close()

    sock.close()

    # return URL on ZMQ channel if specified in extra_prms
    if "zmq_impath_return_ch" in extra_prms:
        try:
            context = zmq.Context()

            impath_sender = context.socket(zmq.REQ)
            impath_sender.connect(extra_prms["zmq_impath_return_ch"])
            impath_sender.send_string(str(out_dict["clean_fn"]))
            impath_sender.recv_string()

        finally:
            impath_sender.close()
            context.term()
