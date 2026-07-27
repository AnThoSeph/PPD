# Deploy PPD API (free) — run from anywhere

Host the API in the cloud so your phone works on **any network**, with **no laptop** and **no tunnel**.

| Method | Laptop required? | Works anywhere? |
|--------|------------------|-----------------|
| **Render (this guide)** | No | Yes |
| Cloudflare quick tunnel | Yes (API + tunnel running) | Yes, while PC is on |
| USB / same Wi‑Fi | Yes or same network | No |

Use **Render’s free web service** ($0).

## Limits of the free tier (important)

| Topic | What to expect |
|-------|----------------|
| Cost | $0 |
| Idle | Service **sleeps** after ~15 minutes of no traffic |
| Cold start | First request after sleep can take **30–90 seconds** |
| Disk | **Ephemeral** — uploads/resumes can reset when the service sleeps or redeploys |
| Always-on | Not available on free; upgrade later if you need it |

For data you care about, export PDF/YAML periodically. Free cloud is fine for editing and preview from the phone.

## 1. Deploy on Render (~10 min)

The PPD repo already includes `Dockerfile` and `render.yaml` on branch `feat/build-ocr-and-cleanup`.

1. Create a free account at [https://render.com](https://render.com) (GitHub login).
2. **New → Blueprint** → connect **AnThoSeph/PPD** → pick branch `feat/build-ocr-and-cleanup` → apply `render.yaml`.
   - Or **New → Web Service** → Docker → plan **Free** → same branch.
3. Wait until status is **Live**.
4. Open `https://YOUR-SERVICE.onrender.com/health` — expect `{"ok":true,...}`.
5. In Render → your service → **Environment** → copy **`PPD_API_KEY`**.

Your public base URL:

```text
https://ppd-api-xxxx.onrender.com
```

(no trailing slash, no `:8765`)

## 2. Point the Flutter app at it

In the app → **API settings**:

| Field | Value |
|-------|--------|
| API base URL | `https://ppd-api-xxxx.onrender.com` |
| API key | the `PPD_API_KEY` from Render |
| Workspace ID | leave as-is (or any stable id) |

Tap **Test connection** → **Save**.

After the server has slept, the first request may be slow — wait and try again.

## 3. Optional local Docker check

```bash
cd PPD
docker build -t ppd-api .
docker run --rm -p 8765:8765 -e PPD_API_KEY=dev-key -e PPD_ALLOW_OPEN=0 ppd-api
curl http://127.0.0.1:8765/health
```

## Other hosts (if Render doesn’t suit you)

| Host | Notes |
|------|--------|
| **Render** | Simplest; free tier with sleep |
| Fly.io | Free allowance; CLI setup |
| Railway | Trial credit only |
| Oracle Cloud free VM | Always-on VPS; more manual setup |

## Security

- Keep `PPD_ALLOW_OPEN=0` and set `PPD_API_KEY` on any public URL.
- Use the same key in the Flutter **API key** field (`X-API-Key` header).