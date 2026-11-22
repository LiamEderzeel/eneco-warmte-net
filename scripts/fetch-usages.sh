#!/usr/bin/env bash
# Fetch the Eneco usages JSON and print it.
# Usage: ENECO_TOKEN=... ENECO_API_KEY=... ENECO_CUSTOMER_ID=... [ENECO_ACCOUNT_ID=1] scripts/fetch-usages.sh [start-date]
# ENECO_TOKEN is the __Secure-next-auth.session-token cookie; ENECO_API_KEY the apikey request header.
set -euo pipefail

: "${ENECO_TOKEN:?set ENECO_TOKEN}"
: "${ENECO_API_KEY:?set ENECO_API_KEY}"
: "${ENECO_CUSTOMER_ID:?set ENECO_CUSTOMER_ID}"

start="${1:-$(date -d '1 year ago' +%Y-%m-01)}"

UA="Mozilla/5.0 (X11; Linux x86_64; rv:152.0) Gecko/20100101 Firefox/152.0"

echo "refreshing session..." >&2
session=$(curl -sS -w '\n%{http_code}' https://www.eneco.nl/mijn-eneco/api/auth/session/ \
  -H "User-Agent: ${UA}" \
  -H "Accept: application/json" \
  -H "Accept-Language: nl-NL" \
  -H "Cookie: __Secure-next-auth.session-token=${ENECO_TOKEN}")
[[ ${session##*$'\n'} == 200 ]] || { echo "session refresh failed (${session##*$'\n'}): ${session%$'\n'*}" >&2; exit 1; }
id_token=$(jq -er .idToken <<<"${session%$'\n'*}") || { echo "no idToken in response: ${session%$'\n'*}" >&2; exit 1; }

response=$(curl -sS -w '\n%{http_code}' "https://api-digital.enecogroup.com/dxpweb/v3/nl/eneco/customers/${ENECO_CUSTOMER_ID}/accounts/${ENECO_ACCOUNT_ID:-1}/usages" \
  -G \
  --data-urlencode "interval=Day" \
  --data-urlencode "aggregation=Month" \
  --data-urlencode "start=${start}" \
  --data-urlencode "extrapolate=false" \
  --data-urlencode "addWeather=false" \
  --data-urlencode "addPreviousYear=false" \
  --data-urlencode "addBudget=false" \
  -H "User-Agent: ${UA}" \
  -H "apikey: ${ENECO_API_KEY}" \
  -H "Authorization: Bearer ${id_token}" \
  -H "Accept: application/json" \
  -H "Accept-Language: nl-NL" \
  -H "Origin: https://www.eneco.nl" \
  -H "Referer: https://www.eneco.nl/")

status=${response##*$'\n'}
body=${response%$'\n'*}
[[ $status == 200 ]] || { echo "usages request failed ($status): $body" >&2; exit 1; }
jq . <<<"$body"
