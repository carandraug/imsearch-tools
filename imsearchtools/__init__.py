from gevent import monkey

from . import engines as query, postproc_modules, process, utils


monkey.patch_all(thread=False, select=False, httplib=False)
