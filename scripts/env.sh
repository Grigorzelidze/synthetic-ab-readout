#!/bin/sh
if [ -z "${PGHOST:-}" ]; then
    ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
    export PGHOST=127.0.0.1
    export PGPORT=54333
    export PGUSER="${USER:-readout}"
    export PGDATABASE=readout
    export PGDATA="$ROOT/.pgdata"
fi
if [ -n "${PG_BIN:-}" ]; then
    PATH="$PG_BIN:$PATH"
    export PATH
fi
