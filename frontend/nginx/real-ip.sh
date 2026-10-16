#!/bin/sh
# Who is the client? Written at start into /etc/nginx/iga/real-ip.conf (included by ../nginx.conf) from:
#   NGINX_TRUSTED_PROXIES  the proxies allowed to say who the client is: empty (the default) = none, the
#                          client is whoever connected; "cloudflare" = Cloudflare's ranges (cloudflare-ips.txt);
#                          and/or addresses or CIDR ranges of your own load balancer, separated by commas or spaces.
#   NGINX_REAL_IP_HEADER   the header those proxies put the client's address in: CF-Connecting-IP with
#                          "cloudflare", X-Forwarded-For otherwise.
#   NGINX_ONLY_FROM_TRUSTED_PROXIES  true = drop every request that didn't come through them (the origin
#                          answers only Cloudflare). A firewall that does the same is better still.
# A request from anywhere else keeps its real address, so a made-up X-Forwarded-For or CF-Connecting-IP
# header changes nothing: rate limits, Django's throttles and the audit log all see the real one. nginx
# also takes X-Forwarded-Proto (http or https) only from these proxies.
set -eu

conf_dir=/etc/nginx/iga
out="$conf_dir/real-ip.conf"
mkdir -p "$conf_dir"

proxies=$(printf '%s' "${NGINX_TRUSTED_PROXIES:-}" | tr ',' ' ')
header="${NGINX_REAL_IP_HEADER:-}"
only_from="${NGINX_ONLY_FROM_TRUSTED_PROXIES:-false}"
ranges=""

for proxy in $proxies; do
    case "$proxy" in
        cloudflare)
            ranges="$ranges $(grep -v '^#' "$conf_dir/cloudflare-ips.txt" | tr '\n' ' ')"
            header="${header:-CF-Connecting-IP}"
            ;;
        *)
            # Addresses and ranges only (nginx checks the rest when it starts).
            if ! printf '%s' "$proxy" | grep -Eq '^[0-9A-Fa-f:.]+(/[0-9]{1,3})?$'; then
                echo "$0: NGINX_TRUSTED_PROXIES: \"$proxy\" is not an address, a CIDR range or \"cloudflare\"" >&2
                exit 1
            fi
            ranges="$ranges $proxy"
            ;;
    esac
done

header="${header:-X-Forwarded-For}"
if ! printf '%s' "$header" | grep -Eq '^[A-Za-z0-9-]+$'; then
    echo "$0: NGINX_REAL_IP_HEADER: \"$header\" is not a header name" >&2
    exit 1
fi

{
    echo "# Written by $0 at start. Do not edit: set NGINX_TRUSTED_PROXIES instead."
    for range in $ranges; do
        echo "set_real_ip_from $range;"
    done
    if [ -n "$(echo $ranges)" ]; then
        echo "real_ip_header $header;"
        echo "real_ip_recursive on;"
    fi
    # 1 when the connection itself came from a trusted proxy.
    echo 'geo $realip_remote_addr $iga_via_trusted_proxy {'
    echo '    default 0;'
    for range in $ranges; do
        echo "    $range 1;"
    done
    echo '}'
    echo 'map $iga_via_trusted_proxy $iga_refuse_direct {'
    echo '    default 0;'
    if [ "$only_from" = "true" ]; then
        if [ -z "$(echo $ranges)" ]; then
            echo "$0: NGINX_ONLY_FROM_TRUSTED_PROXIES=true needs NGINX_TRUSTED_PROXIES" >&2
            exit 1
        fi
        echo '    0 1;'
    fi
    echo '}'
} > "$out"

echo "$0: trusted proxies: $(echo $ranges | wc -w) address ranges${ranges:+, client address from $header}; only from them: $only_from"
