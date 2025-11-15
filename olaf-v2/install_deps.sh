#!/usr/bin/env zsh
# Convenience wrapper: run dependency installer from repo root even when
# executed from inside olaf-v2/
set -euo pipefail

SCRIPT_DIR=${0:A:h}
REPO_ROOT=${SCRIPT_DIR}/..
exec zsh "${REPO_ROOT}/scripts/install_deps.sh"
