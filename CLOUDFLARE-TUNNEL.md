# PPD API via Cloudflare Tunnel (free, no Render)

Use this when your phone is **not** on the same Wi‑Fi as your PC. Cloudflare gives you a public **HTTPS** URL that forwards to your local API.

## Quick tunnel (easiest — no Cloudflare account)

**Terminal 1 — API:**
```powershell
cd C:\Users\anshu\Documents\PPD
ppd serve --host 0.0.0.0 --port 8765
```

**Terminal 2 — tunnel:**
```powershell
cd C:\Users\anshu\Documents\PPD
.\scripts\tunnel.ps1
```

Or directly:
```powershell
cloudflared tunnel --url http://127.0.0.1:8765
```

You’ll see a line like:
```text
https://random-words-here.trycloudflare.com
```

## Flutter app

In **API settings**:

| Field | Value |
|-------|--------|
| API base URL | `https://random-words-here.trycloudflare.com` (no trailing slash) |
| API key | leave empty unless you set `PPD_API_KEY` on the server |

Tap **Test connection** → **Save**.

Works on mobile data or any Wi‑Fi. No USB, no firewall rules, no same-network requirement.

## Tradeoffs

| Topic | Quick tunnel |
|-------|----------------|
| Cost | Free |
| Account | Not required |
| URL | **Changes** every time you restart the tunnel |
| PC | Must be on with API + tunnel running |
| Sleep | Stops when you close the tunnel terminal |

For a **stable URL** later: create a free Cloudflare account, add a named tunnel + custom subdomain. Quick tunnel is enough for now.

## Optional: API key

If you want auth on the tunnel:
```powershell
$env:PPD_API_KEY = "your-secret"
$env:PPD_ALLOW_OPEN = "0"
ppd serve --host 0.0.0.0 --port 8765
```
Use the same key in the Flutter **API key** field.

## Troubleshooting

- **Test connection fails** — confirm `/health` works locally: `http://127.0.0.1:8765/health`
- **URL changed** — restart tunnel, copy the new `trycloudflare.com` URL, Save in app
- **Tunnel closed** — phone can’t reach API until you run `tunnel.ps1` again
