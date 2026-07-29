# GitHub Copilot Instructions

This repo (bluesky) uses the **hbix** platform: **6 REST APIs** for Canadian
building-energy analysis (building codes, geocoding, weather, building stock,
EnergyPlus/OpenStudio modelling lookups, and simulation runs). Other agents in
this repo reach them as MCP servers (see `.mcp.json`), but Copilot in this
environment has **no MCP support** — call the same services over plain HTTP
instead. Every MCP tool has an equivalent REST endpoint behind the same base
URL.

## Base URL and services

```
https://3ucoopudrb.execute-api.ca-central-1.amazonaws.com/prod
```

| Service | Path | MCP equivalent | Purpose |
|---------|------|----------------|---------|
| codes | `/codes` | `mcp__codes__*` | NECB, NBC, ASHRAE 62.1 building codes |
| geocoding | `/geocoding` | `mcp__geocoding__*` | Address geocoding, climate zones, FSA lookup |
| weather | `/weather` | `mcp__weather__*` | EPW/STAT/DDY weather files, design conditions |
| building-stock | `/building-stock` | `mcp__building-stock__*` | Canadian building footprints (NRCan) |
| modelling | `/modelling` | `mcp__modelling__*` | EnergyPlus/OpenStudio IDD schema lookup |
| simulation | `/simulation` | `mcp__simulation__*` | EnergyPlus/OpenStudio/HPXML simulation runs |

The MCP endpoints are just `<base>/<service>/mcp`; the REST endpoints are
everything else under `<base>/<service>/`.

## Auth

Every request needs a per-developer API key sent as `X-API-Key`. Getting one
is **register → admin approval → mint key**, not self-service:

1. `POST /prod/auth/register` (email + password)
2. Wait for an admin to approve the account
3. `POST /prod/auth/me/api-key` (with your Cognito bearer token, or via the
   `/prod/auth/login` page) to mint the key
4. `export HBIX_API_KEY=mk_...`

> The repo's older docs mention "self-registration" — that's out of date.
> Admin approval is required before a key can be minted.

In this workspace the key lives in the gitignored `.env` file, and the
devcontainer's `~/.bashrc` loads it (`set -a && source .env`) so it is already
exported in any terminal. `.mcp.json` and `opencode.json` reference it by name
rather than embedding it. Copy `.env.example` to `.env` and fill in your key;
never paste a real key into a committed file.

## Finding an endpoint (HTTP-contract-first, language-agnostic)

Don't guess endpoint shapes — the API documents itself and the list drifts,
so this file intentionally does not enumerate endpoints. Walk the discovery
chain instead:

1. `GET <base>/llms.txt` — root index: what each service is for
2. `GET <base>/<service>/llms.txt` — that service's tools/endpoints
3. `GET <base>/<service>/openapi.json` — full request/response schemas

Then call any endpoint with `curl`, `fetch`, or any HTTP client in any
language:

```bash
curl -H "X-API-Key: $HBIX_API_KEY" \
  "https://3ucoopudrb.execute-api.ca-central-1.amazonaws.com/prod/codes/search?q=fenestration"
```

> **Windows PowerShell:** `curl` is aliased to `Invoke-WebRequest` there —
> use `curl.exe` for the real curl binary, or `Invoke-RestMethod -Headers
> @{"X-API-Key"=$env:HBIX_API_KEY}`.

## Python accelerator

If you're working in Python, skip hand-rolled `requests` calls:

```bash
curl <base>/client.py -o hbix_client.py
```

```python
from hbix_client import HbixClient

c = HbixClient()  # reads HBIX_API_KEY from env
c.discover()               # list all services
c.codes.discover()         # list codes' tools/endpoints
c.codes.search("necb", "fenestration")
```

## Example session

```
User: What are the thermal transmittance requirements for walls in NECB 2020?

Copilot: curl -H "X-API-Key: $HBIX_API_KEY" \
           "https://3ucoopudrb.execute-api.ca-central-1.amazonaws.com/prod/codes/api/necb/tables/3.2.2.2?edition=2020&division=B"

         Table 3.2.2.2. gives the maximum overall thermal transmittance of
         above-ground opaque assemblies by climate zone. Below-grade walls
         are Table 3.2.3.1.
```

Confirm the exact path against `/codes/openapi.json` before relying on it —
the paths above are illustrative, the schema is authoritative.

## Stable domain facts worth remembering

- **NECB does not define ventilation rates** — it defers to "the applicable
  ventilation standard" (ASHRAE 62.1). For ventilation questions about
  Canadian buildings, query both `codes` (NECB requirements) and the
  ASHRAE 62.1 tables (actual rates) via the same `codes` service.
- **Climate zones**: Canadian climate zones (4, 5, 6, 7A, 7B, 8) are based
  on Heating Degree Days (HDD) and are looked up via `geocoding`.
- **Editions**: `codes` defaults to the newest edition (NECB 2025). Pass
  `edition=2020` explicitly when the question is about NECB 2020.

## Troubleshooting

**401 / 403 responses** — your key is missing, expired, or your account
isn't approved yet. Re-check `HBIX_API_KEY` and your account status via
`GET /prod/auth/me` (bearer token) or the account page at `/prod/auth/login`.

**Interactive docs** — visit `<base>/<service>/docs` (Swagger UI) or
`<base>/<service>/redoc` in a browser for any service, e.g.
`https://3ucoopudrb.execute-api.ca-central-1.amazonaws.com/prod/codes/docs`.
