#!/usr/bin/env bash
set -euo pipefail

case "${1:-api}" in
  api)
    # Only the API initializes schema. Deploy it before starting the worker.
    python -m deployment.init_db
    # Verification and WebSocket URLs carry tokens: omit request/info logs.
    exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}" --no-access-log --log-level warning
    ;;
  worker)
    exec arq agent.worker.WorkerSettings
    ;;
  *)
    echo "Usage: bash deployment/start.sh api|worker" >&2
    exit 2
    ;;
esac
