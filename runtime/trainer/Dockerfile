# syntax=docker/dockerfile:1.7
# Supply an organization-approved LlamaFactory image by immutable digest at build time.
ARG LLAMAFACTORY_IMAGE
FROM ${LLAMAFACTORY_IMAGE}

ARG LLAMAFACTORY_IMAGE
RUN case "$LLAMAFACTORY_IMAGE" in *@sha256:*) ;; *) echo "LLAMAFACTORY_IMAGE precisa usar digest" >&2; exit 1 ;; esac

WORKDIR /opt/hubcontador
COPY runtime/trainer/runner.py ./runner.py

# The parent image supplies CUDA, PyTorch and llamafactory-cli. This layer exposes no
# port and keeps the runner free of Hub, ODBC, database and network credentials.
ENTRYPOINT ["python", "/opt/hubcontador/runner.py"]
