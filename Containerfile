FROM registry.access.redhat.com/ubi9/ubi-minimal@sha256:c0e70387664f30cd9cf2795b547e4a9a51002c44a4a86aa9335ab030134bf392

RUN microdnf install --assumeyes --nodocs --setopt=keepcache=0 python3.12

USER 1001

COPY --chown=1001 . /app

WORKDIR /app

RUN python3.12 -m venv .venv && . ./.venv/bin/activate && pip install -r requirements.txt

ENTRYPOINT ["/bin/bash", "-c", "source /app/.venv/bin/activate && python3.12 /app/migration.py /data"]
