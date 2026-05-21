#!/bin/bash
set -Eeuo pipefail

# Marker to detect first run
INIT_MARKER="${INIT_MARKER:-/home/opc/init/.db_initialized}"

# Prefer sqlplus; fallback to sql
if command -v sqlplus >/dev/null 2>&1; then
  SQLBIN="${SQLBIN:-sqlplus}"
elif command -v sql >/dev/null 2>&1; then
  SQLBIN="${SQLBIN:-sql}"
else
  echo "ERROR: Need sqlplus or sql in PATH (or set SQLBIN)." >&2
  exit 1
fi

# Where the .sql files live (default: alongside this bash script)
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"
SQL_DIR="${SQL_DIR:-$SCRIPT_DIR}"

# --- Load env safely (allow unset while sourcing) ---
set +u
if [[ -f /home/opc/init/variable.sh ]]; then
  source /home/opc/init/variable.sh
elif [[ -n "${HOME:-}" && -f "${HOME%/}/.env" ]]; then
  source "${HOME%/}/.env"
else
  echo "ERROR: Neither /home/opc/init/variable.sh nor ~/.env found." >&2
  exit 1
fi
set -u

# Normalize BASEURL if present
if [[ -n "${BASEURL:-}" ]]; then
  BASEURL="${BASEURL%/}"; BASEURL="${BASEURL%/}"
fi

# Required vars
for v in DBCONNECTION DBPASSWORD; do
  [[ -n "${!v:-}" ]] || { echo "ERROR: Missing required env var: $v" >&2; exit 1; }
done

# ---- Explicit script lists ----
# FULL (first run) — adjust as needed
FULL_ADMIN=(
  prism-setup1.sql
)

# DELTA (re-run) — exactly the files you listed
DELTA_ADMIN=(
  db_setup_script_2.sql
)

# Helper to emit @ lines and fail fast if a file is missing
emit_at_lines() {
  local s
  for s in "$@"; do
    if [[ ! -f "$SQL_DIR/$s" ]]; then
      echo "ERROR: Missing SQL script: $SQL_DIR/$s" >&2
      exit 1
    fi
    printf '@%s\n' "$s"
  done
}

# Decide mode
if [[ -f "$INIT_MARKER" && "${FULL_INIT:-0}" != "1" ]]; then
  MODE="DELTA"
  ADMIN_LIST=("${DELTA_ADMIN[@]}")
else
  MODE="FULL"
  ADMIN_LIST=("${FULL_ADMIN[@]}")
fi
echo "Mode: $MODE"

# Always run from the SQL_DIR so relative @db_setup_*.sql works
pushd "$SQL_DIR" >/dev/null

# --- ADMIN ---
USERNAME=admin
"$SQLBIN" -s /nolog <<EOF
WHENEVER SQLERROR EXIT SQL.SQLCODE
CONNECT ${USERNAME}/${DBPASSWORD}@"${DBCONNECTION}"
DEFINE dbpassword='${DBPASSWORD}'
DEFINE baseurl='${BASEURL:-}'
DEFINE user_ocid='${USER_OCID:-}'
DEFINE tenancy='${TENANCY_OCID:-}'
DEFINE fingerprint='${PEM_KEY_FINGERPRINT:-}'
DEFINE pem_key="${PEM_SINGLE_LINE:-}"
$(emit_at_lines "${ADMIN_LIST[@]}")
EXIT
EOF

# --- Prism only on FULL ---
if [[ "$MODE" == "FULL" ]]; then
  USERNAME=prism
  "$SQLBIN" -s /nolog <<EOF
WHENEVER SQLERROR EXIT SQL.SQLCODE
CONNECT ${USERNAME}/${DBPASSWORD}@"${DBCONNECTION}"
DEFINE dbpassword='${DBPASSWORD}'
DEFINE baseurl='${BASEURL:-}'
DEFINE user_ocid='${USER_OCID:-}'
DEFINE tenancy='${TENANCY_OCID:-}'
DEFINE fingerprint='${PEM_KEY_FINGERPRINT:-}'
DEFINE pem_key="${PEM_SINGLE_LINE:-}"
@prism-setup2.sql
EXIT
EOF

  #mkdir -p "$(dirname "$INIT_MARKER")"
  #: > "$INIT_MARKER"
fi

popd >/dev/null
echo "Done."
