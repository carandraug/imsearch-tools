## Copyright (C) 2023 David Miguel Susano Pinto <pinto@robots.ox.ac.uk>
##
## Copying and distribution of this file, with or without modification,
## are permitted in any medium without royalty provided the copyright
## notice and this notice are preserved.  This file is offered as-is,
## without any warranty.

FROM docker.io/debian:bookworm-slim

RUN apt-get update \
    && apt-get install -y \
        python3-gevent \
        python3-requests \
        python3-pil \
        python3-flask \
        python3-zmq \
        python3-setuptools \
        python3-pip \
    && rm -rf /var/lib/apt/lists/*

COPY . /root/imsearch-tools

## Why these pip install options:
##
##   --no-cache-dir: keep image small, don't keep a copy in the
##      package cache.
##
##   --no-index: we want to install dependencies with apt.  We already
##     installed them so we could have used `--no-deps`.  However,
##     that may cause issues in the future if imsearchtools
##     dependencies change.  `--no-index` states that we do want the
##     dependencies installed but prevents getting them from PyPI.
##
##   --disable-pip-version-check: we don't need to update even if it
##     is an old version.
##
##   --no-build-isolation: see PEP517 for details.  We don't need
##     this, it doesn't apply to creating a Docker image, cause extra
##     copies, and doesn't work with `--no-index`.
##
##   --break-system-packages: this scarily named option forces pip to
##     ignore that it is not the only manager of Python package in the
##     system.  Without it, it will error saying that you should be
##     using virtualenvs.
##
##   --root-user-action ignore: we are installing as root so pip will
##     warn about it.  This silences the warning.
RUN cd /root/imsearch-tools \
    && pip install \
           --no-cache-dir \
           --no-index \
           --disable-pip-version-check \
           --no-build-isolation \
           --break-system-packages \
           --root-user-action ignore \
           . \
    && rm -rf imsearch_tools.eg_info/ build/

ENTRYPOINT ["python3", "-m", "imsearchtools.http_service"]
CMD []
