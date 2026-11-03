#!/bin/sh
set -eu
. "$(dirname "$0")/env.sh"

if [ -n "${PGPASSWORD:-}" ] && [ "${PGHOST:-}" != "127.0.0.1" ]; then
    echo "external postgres, not starting a local cluster"
    exit 0
fi

BIN="${PG_BIN:-}"
if [ -z "$BIN" ]; then
    if command -v initdb >/dev/null 2>&1; then
        BIN=$(dirname "$(command -v initdb)")
    else
        echo "initdb not on PATH; set PG_BIN" >&2
        exit 1
    fi
fi

cmd=${1:-start}
case "$cmd" in
    start)
        mkdir -p "$PGDATA"
        if [ ! -f "$PGDATA/PG_VERSION" ]; then
            "$BIN/initdb" -D "$PGDATA" --username="$PGUSER" --auth-local=trust --auth-host=trust --encoding=UTF8 --locale=C >/dev/null
        fi
        if ! "$BIN/pg_ctl" -D "$PGDATA" status >/dev/null 2>&1; then
            "$BIN/pg_ctl" -D "$PGDATA" -o "-p $PGPORT -k $PGDATA -c listen_addresses=127.0.0.1" -l "$PGDATA/server.log" start
        fi
        ready=0
        i=0
        while [ "$i" -lt 30 ]; do
            if "$BIN/pg_isready" -h 127.0.0.1 -p "$PGPORT" >/dev/null 2>&1; then
                ready=1
                break
            fi
            i=$((i + 1))
            sleep 0.2
        done
        if [ "$ready" -ne 1 ]; then
            echo "postgres did not start; see $PGDATA/server.log" >&2
            exit 1
        fi
        if ! "$BIN/psql" -h 127.0.0.1 -p "$PGPORT" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='${PGDATABASE}'" | grep -q 1; then
            "$BIN/createdb" -h 127.0.0.1 -p "$PGPORT" "$PGDATABASE"
        fi
        ;;
    stop)
        if [ -d "$PGDATA" ]; then
            "$BIN/pg_ctl" -D "$PGDATA" stop || true
        fi
        ;;
    *)
        echo "use start or stop" >&2
        exit 1
        ;;
esac
