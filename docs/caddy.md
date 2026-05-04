# Caddy

The Caddyfile lives on the Hetzner host at `/etc/caddy/Caddyfile`, not in
this repo. This document is the canonical reference for what that file
must look like, and how to keep `openmv.net` / `www.openmv.net` /
`test.openmv.net` on the right certificates.

Reload after every edit:

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

## Why two site blocks, not one

`openmv.net` and `www.openmv.net` are proxied through Cloudflare (orange
cloud). Cloudflare presents a public-trust cert to visitors at the edge
and re-encrypts to origin in `Full (strict)` mode. The origin cert
Cloudflare validates against is a **Cloudflare Origin Certificate** —
signed by Cloudflare's internal CA, not by any public CA — at
`/etc/caddy/origin-certs/openmv.net/`. That cert is **only** trusted
when Cloudflare's edge is the one consuming it.

`test.openmv.net` is intentionally DNS-only (grey cloud) so the
maintainer can reach the origin directly and exercise the site without
Cloudflare's caching / Bot Fight Mode in the path. There is no
Cloudflare edge in front of `test.openmv.net`, which means whatever cert
Caddy serves goes straight to the visitor's browser (or `urllib`,
`pandas.read_csv`, etc.).

If `test.openmv.net` shares a site block with the prod hostnames, Caddy
serves the Cloudflare Origin Certificate for it too — and every direct
client gets `net::ERR_CERT_AUTHORITY_INVALID` /
`URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] ...>` because
the Cloudflare Origin CA is not in any browser or Python trust store
(issue #89). The fix is to give `test.openmv.net` its own site block
with no `tls` directive, so Caddy issues a Let's Encrypt cert via the
ACME HTTP-01 challenge automatically.

## Canonical structure

```caddyfile
# Shared behaviour for all three hostnames. Keep this in one place so prod
# and staging cannot drift apart on what /static, /media, or upstream looks
# like.
(openmv_common) {
    encode zstd gzip

    handle_path /static/* {
        root * /home/deploy/openmv/repo/data/static
        file_server
    }

    handle_path /media/* {
        root * /home/deploy/openmv/repo/data/media
        file_server
    }

    # Apache-era files that used to be aliased on disk.
    @public path /robots.txt /favicon.ico /blender-efficiency.xlsx
    handle @public {
        root * /home/deploy/openmv/repo/data/public
        file_server
    }

    reverse_proxy 127.0.0.1:8001 {
        header_up X-Forwarded-Proto https
    }
}

# Production: behind Cloudflare (orange cloud), Full (strict) mode.
# The cert here is consumed by Cloudflare's edge, not by visitors directly,
# so a Cloudflare Origin Certificate is correct.
openmv.net, www.openmv.net {
    tls /etc/caddy/origin-certs/openmv.net/cert.pem /etc/caddy/origin-certs/openmv.net/key.pem
    import openmv_common
}

# Staging: DNS-only (grey cloud). Visitors hit Caddy directly, so Caddy
# MUST present a publicly-trusted cert. No `tls` directive → Caddy uses
# its default automatic-HTTPS path and issues a Let's Encrypt cert via
# the ACME HTTP-01 challenge on port 80.
test.openmv.net {
    import openmv_common
}
```

The two site blocks intentionally do not share a `tls` directive —
that's the whole point. If you ever add a fourth hostname, decide first
whether it lives behind Cloudflare's proxy (Origin Cert site block) or
in front of it (Let's Encrypt site block) and put it in the matching
block.

## Verifying

After `systemctl reload caddy`, confirm the cert chain on each hostname:

```bash
# Public-trust chain (Let's Encrypt → ISRG Root X1):
echo | openssl s_client -connect test.openmv.net:443 -servername test.openmv.net 2>/dev/null \
  | openssl x509 -noout -issuer -subject -dates

# Cloudflare Origin CA (only valid behind Cloudflare's proxy):
echo | openssl s_client -connect openmv.net:443 -servername openmv.net 2>/dev/null \
  | openssl x509 -noout -issuer -subject -dates
```

`test.openmv.net` should report `issuer=C=US, O=Let's Encrypt, CN=R10`
(or whichever Let's Encrypt intermediate is current). If you see
`issuer=C=US, O=CloudFlare, Inc., CN=CloudFlare Origin Certificate`
on `test.openmv.net`, the site block is wrong — it's importing the
production `tls` directive.

The Python smoke-test from issue #89 should also succeed:

```bash
python -c "import pandas as pd; print(pd.read_csv('https://test.openmv.net/file/aeration-rate.csv').head())"
```

If it fails with `URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED]...>`,
re-check the Caddyfile and the `openssl s_client` output above.

## If Let's Encrypt issuance is failing

Caddy logs the ACME exchange. Tail it while reloading:

```bash
sudo journalctl -u caddy -f
```

Common causes of a failed HTTP-01 challenge for `test.openmv.net`:

1. **Cloudflare proxy still on (orange cloud).** The challenge has to
   reach Caddy on port 80 directly. The DNS record must be grey-cloud.
2. **Port 80 not reachable from the public internet.** The Hetzner
   firewall and Hetzner Cloud's network firewall both need to allow TCP
   80 from `0.0.0.0/0`. Verify with
   `curl -I http://test.openmv.net/` from off-host.
3. **A previous failed issuance is still cached.** Caddy keeps trying;
   if you've fixed the underlying cause and want to force a retry,
   `sudo systemctl restart caddy` is enough — there's no need to delete
   `/var/lib/caddy/`.
4. **Let's Encrypt rate limit (50 certs/week per registered domain).**
   Unusual for this site, but if it ever happens the issuance falls back
   to Caddy's internal CA and the symptom is identical to issue #89.
   Check the journal for `429 urn:ietf:params:acme:error:rateLimited`.
