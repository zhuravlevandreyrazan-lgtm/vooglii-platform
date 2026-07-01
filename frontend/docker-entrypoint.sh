#!/bin/sh
set -eu

RUNTIME_API_BASE_URL="${NEXT_PUBLIC_API_BASE_URL:-}"
RUNTIME_APP_ENV="${NEXT_PUBLIC_APP_ENV:-production}"

cat > /app/public/runtime-config.js <<EOF
window.__VOOGLII_RUNTIME_CONFIG__ = {
  NEXT_PUBLIC_API_BASE_URL: "${RUNTIME_API_BASE_URL}",
  NEXT_PUBLIC_APP_ENV: "${RUNTIME_APP_ENV}"
};
EOF

exec node server.js
