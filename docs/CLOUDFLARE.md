# Putting Iga behind Cloudflare

Iga protects itself against one client, or a few, sending too much: nginx limits requests and connections per address and drops slow clients early, and Django limits each account and each signed-in user (see "Rate limits" in [ARCHITECTURE.md](ARCHITECTURE.md#security-and-privacy)). None of that helps against a distributed attack: thousands of addresses can fill the server's internet link before nginx sees a single request. Only a network in front of the server, with far more capacity than any school server, can absorb that. This guide puts Iga behind Cloudflare (its free plan is enough to start); any similar service works the same way.

What changes: browsers talk to Cloudflare, Cloudflare talks to your server, and your server answers only Cloudflare.

```
Browser ──HTTPS──► Cloudflare (WAF, rate limits, bots, cache) ──HTTPS──► nginx (your server) ──► Django
```

## 1. DNS: proxied records

1. Add your domain to Cloudflare and change its name servers at your registrar to the two Cloudflare gives you.
2. Create an `A` record (and `AAAA` for IPv6) for the app, for example `iga.example.rw`, pointing to your server, with **Proxy status: Proxied** (the orange cloud). Proxied records answer with Cloudflare's addresses, so your server's address stays private.
3. Don't leave other records on the same server unproxied (`direct.`, `ftp.`, `mail.`): they would give its address away. If the address was public before, ask your host for a new one once everything goes through Cloudflare.

## 2. HTTPS: Full (strict)

1. **SSL/TLS → Overview: Full (strict).** Cloudflare then connects to your server over HTTPS and checks its certificate. Never use **Flexible**: Cloudflare would talk to your server over plain HTTP, so passwords and session cookies would cross the internet unencrypted between Cloudflare and you.
2. Give nginx a certificate. The simplest is a **Cloudflare Origin CA certificate** (SSL/TLS → Origin Server → Create certificate: valid up to 15 years, trusted only by Cloudflare, which is all it needs to be). Save the certificate and key on the server and switch on nginx's HTTPS as described in [README.md](../README.md#https) (`frontend/nginx/tls.conf.example`). A Let's Encrypt certificate works too.
3. **SSL/TLS → Edge Certificates:** Always Use HTTPS on; Minimum TLS Version 1.2; TLS 1.3 on. Iga already sends HSTS itself (nginx for the app, Django for the API, one year with subdomains, `preload` only with `HSTS_PRELOAD=true`), so leave Cloudflare's HSTS setting off, or give it the same values.

## 3. Iga's settings

In `.env`:

```
NGINX_TRUSTED_PROXIES=cloudflare
NGINX_ONLY_FROM_TRUSTED_PROXIES=true
DJANGO_ALLOWED_HOSTS=iga.example.rw
CSRF_TRUSTED_ORIGINS=https://iga.example.rw
FRONTEND_URL=https://iga.example.rw
# HTTPS=false must not be there: HTTPS is on by default.
# TRUSTED_PROXY_COUNT stays 1 (Django trusts nginx, and nginx trusts Cloudflare).
```

What this does:

- **Real client addresses.** Cloudflare sends the visitor's address in `CF-Connecting-IP`. nginx believes that header only when the connection itself comes from one of Cloudflare's published ranges (`frontend/nginx/cloudflare-ips.txt`), and then passes exactly that address to Django. Rate limits, sign-in lockouts and the audit log see the real student, not Cloudflare. Without this setting every student would share Cloudflare's few addresses and one school's sign-ins could lock out everyone; with it set but no origin lock, a request sent straight to your server still can't pretend to be anyone else, because nginx ignores the header from addresses outside Cloudflare's ranges.
- **HTTP or HTTPS.** nginx takes `X-Forwarded-Proto` from Cloudflare only, so Django's secure cookies, HSTS and HTTPS redirects work without redirect loops.
- **Origin lock.** `NGINX_ONLY_FROM_TRUSTED_PROXIES=true` makes nginx drop, without an answer, every request that didn't come through Cloudflare.

Cloudflare's ranges change rarely. Compare `frontend/nginx/cloudflare-ips.txt` with <https://www.cloudflare.com/ips-v4> and <https://www.cloudflare.com/ips-v6> before going live and now and then (the file says how to refresh it), and rebuild the `web` image after a change.

## 4. Lock the origin to Cloudflare

The nginx setting above is the second layer; the first is a firewall that lets only Cloudflare reach ports 80 and 443, so nobody else can even open a connection:

- **Your host's firewall** (cloud security group, Hetzner/OVH firewall, ...): allow TCP 443 (and 80, for redirects) from Cloudflare's ranges only, and SSH from your own address.
- **On the server itself**, remember that Docker publishes ports past `ufw`: its own iptables rules come first. Filter in the `DOCKER-USER` chain instead, for example:

  ```sh
  # Only Cloudflare may reach the published HTTPS port (IPv4; repeat with ip6tables and the IPv6 ranges).
  # The DROP goes in first, then each range is inserted above it.
  iptables -I DOCKER-USER -p tcp -m conntrack --ctorigdstport 443 -j DROP
  for range in $(grep -v '^#' frontend/nginx/cloudflare-ips.txt | grep -v ':'); do
      iptables -I DOCKER-USER -p tcp -m conntrack --ctorigdstport 443 -s "$range" -j RETURN
  done
  ```

  Do the same for port 80 if you publish it, and make the rules survive a reboot (`iptables-persistent`).

- **Stronger:** turn on **Authenticated Origin Pulls** (SSL/TLS → Origin Server) and have nginx require Cloudflare's client certificate (`ssl_client_certificate` with Cloudflare's origin-pull CA, `ssl_verify_client on;` in `tls.conf`); or use **Cloudflare Tunnel** (`cloudflared`), which needs no open inbound port at all.

Check it: `curl -sI https://iga.example.rw/api/health/` answers through Cloudflare, while `curl -k --resolve iga.example.rw:443:<your server's address> https://iga.example.rw/` from another machine gets no answer.

## 5. WAF managed rules

**Security → WAF → Managed rules:** deploy the **Cloudflare Managed Ruleset** (the **Free Managed Ruleset** on the free plan) and, on paid plans, the **OWASP Core Ruleset** at paranoia level 1 with the action *Managed Challenge* or *Block*. Watch **Security → Events** for a week: two Iga features legitimately send text that looks like attacks to generic rules, so add exceptions for them if they trip:

- `/api/code/` (students' C++ and Java source code),
- `/api/lessons/`, `/api/questions/`, `/api/quizzes/` (teachers' Markdown, which may contain HTML-like text).

Iga checks all input itself; the WAF is an extra filter, not the only one.

## 6. Rate limiting rules

**Security → WAF → Rate limiting rules.** These catch floods at Cloudflare's edge before they reach you. Count per IP, and keep them at or above nginx's limits (`NGINX_RATE_*`) so that a school's normal morning rush passes and only floods are stopped. Remember that a whole school often shares one public address.

| Rule | Expression | Limit | Action |
|---|---|---|---|
| Sign-in and account | `http.request.method eq "POST" and http.request.uri.path matches "^/api/auth/(login\|register\|password-reset\|password\|2fa\|step-up)/"` | 60 per minute per IP | Block (or Managed Challenge) for 10 minutes |
| Costly | `starts_with(http.request.uri.path, "/api/tutor/") or http.request.uri.path eq "/api/code/run/" or (starts_with(http.request.uri.path, "/api/billing/") and not starts_with(http.request.uri.path, "/api/billing/webhooks/"))` | 120 per minute per IP | Block for 1 minute |
| Whole API | `starts_with(http.request.uri.path, "/api/")` | 3,000 per minute per IP | Block for 1 minute |

The free plan allows one rule with a 10-second period: use it for sign-in (for example 15 requests per 10 seconds). Leave Flutterwave's webhook (`/api/billing/webhooks/flutterwave/`) out of every rule and challenge: Iga checks its signature, and a blocked webhook only delays a payment (the scheduler asks Flutterwave about open payments every 10 minutes anyway).

## 7. Bots

**Security → Bots: Bot Fight Mode** on (free). Two cautions:

- On the free plan Bot Fight Mode can't be skipped for particular paths and may challenge Flutterwave's webhook. If payments stop arriving by webhook (Admin → Schools shows them confirmed only by the 10-minute check), turn it off, or on a paid plan use **Super Bot Fight Mode** with a WAF skip rule for `/api/billing/webhooks/`.
- Leave "Definitely automated" traffic on *Block* or *Managed Challenge*, not on JS challenge for the API: the app's own requests come from a browser that has already passed any challenge on the page, so they are not affected.

**Under Attack Mode** (Overview) puts a check in front of every visitor; use it only during an attack.

## 8. Caching

Cloudflare caches common static file types by default and never caches API answers unless told to. Add **Caching → Cache Rules** so that the app's files are cached as Iga intends:

| Paths | Setting |
|---|---|
| `/assets/*` | Eligible for cache; Edge and Browser TTL: respect origin (Iga sends one year, `immutable`: file names change with every release) |
| `/pyodide/*`, `/runtimes/*` | Eligible for cache; respect origin (30 days) |
| `/api/*`, `/django-admin/*`, `/protected-media/*` | **Bypass cache** |
| `/`, `/index.html`, `/sw.js`, `/manifest.webmanifest` | Respect origin (not cached for long), so a new release reaches students at once |

Never use "Cache Everything" on `/api/`: Cloudflare would serve one student's answers, marks or profile to another. Uploaded media (`/media/`) can follow the origin's 7 days.

## 9. Cloudflare features to leave off

Iga's Content-Security-Policy allows only the app's own scripts, so Cloudflare features that inject scripts into pages would be blocked (and they would change what the policy protects): leave **Rocket Loader**, **Email Address Obfuscation**, **Zaraz** and **Web Analytics automatic setup** off. **Automatic HTTPS Rewrites**, **HTTP/3**, **Brotli** and **0-RTT** (keep off: 0-RTT requests can be replayed) are safe to choose as you like.

## 10. Honest limits

- Cloudflare absorbs floods aimed at the domain name; it can't protect an origin address that attackers already know, which is why the origin lock (step 4) matters.
- Per-IP limits are coarse when a school shares one address. The precise limits are Django's, per account and per user.
- Rate limits stop abuse, not every expensive request: a few hundred students asking Santa at once will still find Santa busy (`SANTA_PARALLEL`) and get answers from the lessons.
