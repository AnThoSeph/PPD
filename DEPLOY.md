# Deploy PPD API (free)

Use **Render’s free web service**. Your phone can call it from any network (Wi‑Fi or mobile data).

## Limits of the free tier (important)

| Topic | What to expect |
|-------|----------------|
| Cost | $0 |
| Idle | Service **sleeps** after ~15 minutes of no traffic |
| Cold start | First request after sleep can take **30–90 seconds** |
| Disk | **Ephemeral** — uploads/resumes can reset when the service sleeps or redeploys |
| Always-on | Not available on free; upgrade later if you need it |

For day-to-day editing that must survive restarts, keep a local backup (export PDF / YAML). Free cloud is ideal for **demux + preview from the phone**.

## 1. Push this repo to GitHub

The API Docker files live in the `PPD` repo. Commit and push the branch that contains `Dockerfile`, `render.yaml`, and `ppd/http_server.py` (or merge to `main`).

## 2. Deploy on Render

1. Create a free account at [https://render.com](https://render.com) (GitHub login is easiest).
2. **New → Blueprint** → connect the **PPD** repo → select `render.yaml`.
3. Or **New → Web Service** → connect repo → Runtime **Docker** → plan **Free**.
4. Wait until the deploy is **Live**. Open `https://YOUR-SERVICE.onrender.com/health` — you want `{"ok":true,...}`.
5. In Render → your service → **Environment**, copy the generated **`PPD_API_KEY`**.

Your public base URL looks like:

```text
https://ppd-api-xxxx.onrender.com
```

(no trailing slash, no `:8765`)

## 3. Point the Flutter app at it

In the app → **API settings**:

| Field | Value |
|-------|--------|
| API base URL | `https://ppd-api-xxxx.onrender.com` |
| API key | the `PPD_API_KEY` from Render |
| Workspace ID | leave as-is (or any stable id) |

Tap **Test connection** → **Save**.

First open after the server slept: wait through the cold start, then test again.

## 4. Optional local check of the image

```bash
cd PPD
docker build -t ppd-api .
docker run --rm -p 8765:8765 -e PPD_API_KEY=dev-key -e PPD_ALLOW_OPEN=0 ppd-api
curl http://127.0.0.1:8765/health
```

## Alternatives (also free tiers)

| Host | Notes |
|------|--------|
| **Render** (this guide) | Simplest Docker free web service |
| Railway | Trial credit, not lasting free |
| Fly.io | Free allowance; more CLI setup |
| Cloudflare Tunnel | Free, but API still runs on your PC |

## Security

- Keep `PPD_ALLOW_OPEN=0` and always set `PPD_API_KEY` on a public URL.
- Put the same key in the Flutter **API key** field (`X-API-Key` header).
