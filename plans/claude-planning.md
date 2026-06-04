# c0ll3ct1v3 Media Platform Roadmap

> Living planning document. Update this file as decisions are made and phases complete.

---

## 1. Product North Star

| Surface | URL | Audience | Purpose |
|---|---|---|---|
| Workbench (internal) | `{artist}.c0ll3ct1v3.xyz` | Artist + agents | Upload, develop, promote to gallery |
| Public EPK (external) | `c0ll3ct1v3.xyz/{artist}` | Bookers (hybrid fan page later) | Hero video + photos + bio; fast slot updates |
| Gallery staging (sub-zone) | Same bucket, `gallery/staging/` | Client / collaborator screening | Pre-public review inside gallery rules |

**v1 EPK content:** YouTube hero embed + gallery photos + bio. Fixed `booker_v1` template — no Design Studio. Worst failure mode is slow curation; prefer slot-swap commands ("replace EPK video with asset X") over manual layout work.

---

## 2. Core Principles

These are fixed constraints, not preferences. Every implementation decision should be checked against them.

**Immutability.** Gallery delivery objects are never overwritten. "Replace EPK hero video" means promoting a new revision (`r{n+1}`) and updating the EPK slot pointer — never mutating an existing key. Any URL ever published to the world must continue to resolve.

**Promote = copy.** Moving something from workbench to gallery is always a copy operation. The workbench master is never deleted or moved. `lineage_id` ties the gallery item back to its workbench origin. You can always go back and remix.

**Hard prefix barriers.** Workbench and gallery are separated by key prefix, not just a database flag. Upload init rejects any key that doesn't start with `workbench/`. The public EPK resolver only reads `gallery/delivery/`. These are enforced in code, not convention.

**Both assets always persist.** Raw workbench masters and finished gallery items coexist indefinitely. Storage is cheap; losing a raw master is not recoverable.

**Derivatives never live in workbench.** Thumbnails, transcodes, HLS segments, and waveforms are always generated into gallery paths, never back into workbench.

---

## 3. Derivatives Glossary

This is the canonical reference for where each file type lives. When in doubt, consult this table.

| Kind | Examples | Lives in |
|---|---|---|
| Master | WAV, ProRes, full-res JPEG, raw stems | `workbench/` only |
| Delivery | Published MP3, web JPEG, compressed video | `gallery/delivery/.../` |
| Derived | Thumbnail, web transcode, HLS segments, waveform PNG | `gallery/delivery/{contentId}/{rev}/derived/` |

Ingest worker runs on workbench upload (audio analysis, basic metadata extraction). Derivative generation only triggers on promotion into gallery — never writes back to workbench.

---

## 4. Current State (Baseline)

**Storage today:**
- Single MinIO bucket `pj-media`
- Upload → `tenants/{slug}/masters/{assetId}/vN/file`
- Publish → `tenants/{slug}/public/{assetId}/published.ext`

**Data model today:**
- One `MediaAsset` table with `status` enum: `inbox → processing → ready → published`
- Flexible `tags` JSONB column
- No lineage, no workbench/gallery distinction

**Public reads today:**
- EPK resolver reads from `public/` prefix
- Transcodes/derivatives: `media-worker` writes `MediaVariant` rows (currently no prefix enforcement)

**The problem:** `status=published` conflates "ready to work with" and "live on the public EPK." There is no structural barrier between private creative work and public-facing assets.

---

## 5. Target Architecture

### Object Key Conventions (one bucket, hard prefixes)

| Zone | Prefix pattern | Writable by | Notes |
|---|---|---|---|
| Workbench | `tenants/{slug}/workbench/{assetId}/v{n}/{filename}` | Portal upload, ingest worker | Raw masters; no public ACL |
| Gallery delivery | `tenants/{slug}/gallery/delivery/{contentId}/r{rev}/{filename}` | Promotion job only | Immutable — new rev = new key |
| Gallery staging | `tenants/{slug}/gallery/staging/{contentId}/r{rev}/...` | Promotion (staging flag) | Same copy rules; not linked from public EPK until released |
| Gallery derived | `tenants/{slug}/gallery/delivery/{contentId}/r{rev}/derived/...` | Derivative worker | Thumbnails, HLS, waveforms |

### Database Structure (target)

```
visions
  id, tenant_slug, title, vision_type (song|film|campaign|...), created_at

timelines
  id, vision_id, label ("Release", "Alt mix", "EPK cut"), sort_order

workbench_assets
  id, timeline_id, storage_key, mime, asset_type, provenance JSONB,
  created_at, created_by

gallery_items
  id, timeline_id, lineage_id (→ workbench_assets.id),
  content_id (stable UUID across revs), rev (integer),
  storage_key, gallery_stage (staging|released),
  immutable_url_slug, promoted_at

engagement_events
  id, tenant_slug, event_type, target_type, target_id,
  session_id, referrer, user_agent, created_at
```

**DaVinci analogy:** Vision = project file; Timeline = version lane (Release, Alt mix, EPK cut); workbench_assets and gallery_items = clips on those timelines.

### EPK Config (on Artist record)

```json
{
  "epk_public": {
    "template": "booker_v1",
    "hero_video": { "type": "youtube", "url": "https://..." },
    "photos": [{ "gallery_content_id": "...", "rev": 1 }],
    "bio": "...",
    "booking_email": "..."
  }
}
```

Slot swap = `PATCH /artists/me/epk-public` with `{ "hero_video": { "gallery_content_id": "..." } }`. Server validates that the referenced item exists, is `gallery_stage=released`, and belongs to the same tenant.

---

## 6. Architecture Decision Records (ADRs)

Decisions that affect URL stability, security boundaries, or core data shape. Revisit these before starting the relevant phase, not during.

### ADR-001: `content_id` stability across gallery revisions

**Decision:** On first promotion of a workbench asset to gallery, assign a new `content_id` UUID. This ID is stable across all future revisions of that gallery item. EPK slots point to `{content_id, rev}`. Incrementing `rev` (r1 → r2) does not change `content_id`.

**Why:** Public URLs and EPK slot references must survive content updates. Tying URLs to `asset.id` (the workbench row) would require updating every external reference on each re-upload.

**Implication:** Do not reuse `workbench_assets.id` as `gallery_items.content_id`. Generate a new UUID at promotion time.

---

### ADR-002: Gallery staging access control

**Decision (pending):** Staging items are accessible only via presigned URLs with expiry, not stable public URLs. The expiry window TBD (suggest 7 days). No password-link system for v1.

**Open question:** Should staging presigned URLs be scoped to a session or shareable with a collaborator? Resolve before Phase 2 ships.

---

### ADR-003: Phase 1 migration strategy

**Decision:** Dual-read fallback for 30 days post-migration. EPK resolver checks `gallery/delivery/` first; falls back to legacy `public/` prefix if not found. Migration script copies `masters/*` → `workbench/` and `public/*` → `gallery/delivery/` without deleting originals. After 30 days, remove fallback and archive legacy prefixes.

**Why not rename in place:** Avoids any window where old keys are gone and new resolver isn't deployed yet.

---

### ADR-004: Single table extension vs. full split in Phase 1

**Decision:** Phase 1 extends `MediaAsset` in place (adds `storage_region`, `gallery_rev`, `parent_asset_id` columns). Phase 2 migrates to `visions / timelines / workbench_assets / gallery_items`. This is intentionally two migrations.

**Rationale:** The alternative — doing the full split in Phase 1 — delays the storage barrier fix (the most urgent correctness issue) while also designing a new schema. Doing them together risks shipping neither cleanly. Accept the tech debt; Phase 2 migration will be straightforward because the lineage data is already captured via `parent_asset_id`.

---

## 7. Phases

### Phase 1 — Workbench / Gallery Split

**Goal:** Correct storage layout and API guardrails. Public EPK still resolves. No new schema complexity yet.

**Exit criteria:**
- New uploads land exclusively under `workbench/` — no exceptions
- Promotion creates an immutable `gallery/delivery/` key; workbench master is unchanged
- Public EPK resolves correctly (via dual-read fallback during migration window)
- Zero `workbench/` objects are served on any public URL

#### 1.1 Storage Layer

- Add `backend/app/services/storage_paths.py` with:
  - `workbench_master_key(slug, asset_id, version, filename)`
  - `gallery_delivery_key(slug, content_id, rev, filename)`
  - `gallery_staging_key(slug, content_id, rev, filename)`
  - `assert_workbench_key(key)` — raises if key doesn't start with `workbench/`
  - `assert_gallery_key(key)` — raises if key doesn't start with `gallery/`
- Change upload init in `media/router.py`: `masters/` → `workbench/`
- Change promote: `public/` → `gallery/delivery/{contentId}/r1/...` (use `asset.id` as interim `contentId` until Phase 2)
- Migration script: copy `tenants/*/masters/*` → `workbench/`, `public/*` → `gallery/delivery/`; dual-read fallback for 30 days

#### 1.2 Data Model (Minimal Extension)

Extend `MediaAsset` via migration — do not create new tables yet:

| Column | Type | Notes |
|---|---|---|
| `storage_region` | enum `workbench\|gallery` | Replaces overloaded `status=published` |
| `gallery_rev` | integer | Default 1 for delivery objects |
| `parent_asset_id` | nullable FK → MediaAsset | Workbench → gallery lineage |
| `gallery_stage` | enum `staging\|released` | Replaces `status=published` for gallery items |
| `epk_role` | nullable enum | `hero_video\|photo\|audio` — required before Phase 3 |

**Note:** `epk_role` is load-bearing for Phase 3 slot binding. It must be populated before Phase 3 starts. Don't treat it as purely optional.

Workbench assets remain `status=ready`; gallery items use `gallery_stage` for visibility.

#### 1.3 Promotion Pipeline

Document the exact sequence — this is the most complex operation in the system:

1. Client calls `POST /media/assets/{id}/promote` with `{ "stage": "staging|released" }`
2. API validates: asset exists, belongs to tenant, `storage_region=workbench`
3. Worker job enqueued: `{ type: "promote", asset_id, stage, target_rev: 1 }`
4. Worker copies workbench key → gallery delivery key (server-side copy, no download)
5. Worker generates derivatives into `gallery/delivery/{contentId}/r1/derived/`
6. DB write (transaction): insert `MediaAsset` row with `storage_region=gallery`, `parent_asset_id`, `gallery_stage`, `gallery_rev=1`
7. On success: return new gallery asset ID to client
8. On failure (copy succeeded, DB write failed): log orphaned key for cleanup job; return 500; do not leave DB row pointing at missing key

#### 1.4 API Changes

| Endpoint | Change |
|---|---|
| `POST /media/uploads/init` | Enforce `workbench/` prefix; reject `gallery/` writes |
| `POST /media/assets/{id}/promote` | Rename from `/publish`; implement pipeline above |
| `GET /media/assets` | Add `?region=workbench\|gallery&stage=staging\|released` filters |
| `GET /media/assets/{id}/preview-url` | Workbench → presigned URL; gallery released → stable CDN URL |

Update `epk_media_resolve.py`: replace `public/` path checks with `gallery/delivery/`.

#### 1.5 Portal UX (Thin)

- Library tabs: **Workbench** | **Gallery** (with Staging filter in Gallery)
- Workbench actions: "Promote to Staging" / "Promote to Gallery"
- Gallery actions: "Release to EPK pool" (staging → released)
- No Design Studio dependency for these flows

#### 1.6 Artist Onboarding Seed Script

- Create seed script for first artist tenant: creates workbench prefix, empty EPK config, default `booker_v1` template
- Required before Phase 3 — don't wait until then

---

### Phase 2 — Metadata: Vision / Timeline / Lineage

**Goal:** Model "archetypal vision" — one song or project with dev versions, a release, and alt releases under one umbrella. Migrate from monolithic `MediaAsset` to structured tables.

**Exit criteria:**
- All assets belong to a vision and at least one timeline
- Lineage from workbench asset → gallery item is queryable
- Old `MediaAsset` rows migrated with `lineage_id` intact
- `content_id` stability confirmed across gallery revisions (ADR-001 implemented)

#### 2.1 New Tables

```sql
-- One creative vision (song, film, campaign, etc.)
visions (
  id UUID PRIMARY KEY,
  tenant_slug TEXT,
  title TEXT,
  vision_type TEXT,  -- song|film|campaign|writing|...
  created_at TIMESTAMPTZ
)

-- Version lanes within a vision
timelines (
  id UUID PRIMARY KEY,
  vision_id UUID REFERENCES visions,
  label TEXT,        -- "Release", "Alt mix", "EPK cut", "Dev v2"
  sort_order INTEGER,
  created_at TIMESTAMPTZ
)

-- Raw creative assets on a timeline
workbench_assets (
  id UUID PRIMARY KEY,
  timeline_id UUID REFERENCES timelines,
  storage_key TEXT,
  mime_type TEXT,
  asset_type TEXT,   -- audio|video|image|document
  provenance JSONB,  -- {source: upload|agent|export, parent_id, agent_run_id, created_by}
  metadata JSONB,    -- flexible: BPM, key, word_count, etc. (stable shape deferred to later)
  created_at TIMESTAMPTZ,
  created_by TEXT
)

-- Published gallery items linked back to workbench
gallery_items (
  id UUID PRIMARY KEY,
  timeline_id UUID REFERENCES timelines,
  lineage_id UUID REFERENCES workbench_assets,
  content_id UUID,   -- stable across revs (ADR-001)
  rev INTEGER,
  storage_key TEXT,
  gallery_stage TEXT,         -- staging|released
  immutable_url_slug TEXT,
  promoted_at TIMESTAMPTZ
)
```

#### 2.2 Metadata Strategy

Detailed audio features, genre, BPM, rights fields, campaign tags: store in `metadata JSONB` on `workbench_assets` and `gallery_items` until shape stabilizes. Mark for a dedicated metadata design pass before Phase 5 agent work begins.

#### 2.3 Rights / Visibility Gate

No boolean "ok for public EPK" field. Rights enforcement is systematic: only `gallery_items` with `gallery_stage=released` are eligible for EPK slot binding. The promotion pipeline is the gate — if it isn't released, it cannot appear on the public EPK. This is checked server-side on every EPK slot update.

#### 2.4 API

- `GET/POST /visions`
- `GET/POST /visions/{id}/timelines`
- `POST /timelines/{id}/workbench/upload` (wraps existing multipart)
- `POST /workbench/{id}/promote` → creates `gallery_items` row + copy
- `GET /gallery?stage=released|staging&vision_id=...`

---

### Phase 3 — Public EPK

**Goal:** `c0ll3ct1v3.xyz/{artist}` live and updatable with a single API call.

**Prerequisite:** `epk_role` column populated (Phase 1.2), at least one released gallery item per slot type.

**Exit criteria:**
- EPK URL resolves for at least one artist with no auth
- Hero video swap completes in under 5 seconds perceived latency
- Zero workbench objects accessible via public EPK URLs
- New artist can go from workbench upload → promote → EPK live without touching Design Studio

#### 3.1 EPK Slot Swap API

`PATCH /artists/me/epk-public`

```json
{ "hero_video": { "gallery_content_id": "uuid-here" } }
```

Server validates on every update:
1. Referenced `gallery_content_id` exists
2. `gallery_stage = released`
3. Tenant matches artist record
4. `epk_role` matches slot type (hero_video, photo, audio)

#### 3.2 Public Frontend

- Route: `/a/:artistSlug` or host-based routing
- `GET /epk/public/{slug}` — no auth; returns template + resolved URLs
- Photos: stable MinIO delivery URLs
- Video: YouTube iframe embed (`hero_video.type = "youtube"`)
- Future self-host: schema already supports `hero_video.type = "gallery"` pointing at `immutable_url_slug` with CDN in front of MinIO

#### 3.3 Hybrid Fan Page

Same data model; alternate `fan_v1` template later with warmer copy and more photos. `booker_v1` stays default. No code changes needed to EPK config schema.

#### 3.4 DNS (Ops Note — see DEPLOYMENT.md)

- `*.c0ll3ct1v3.xyz` → portal (Auth0)
- `c0ll3ct1v3.xyz/{artist}` → public EPK (static or SSR)

Not a code blocker for Phases 1–2. Document routing config in `DEPLOYMENT.md`, not here.

---

### Phase 4 — Engagement Tracking

**Goal:** Industry-standard metrics, anonymous sessions, data-only (no automation).

**Exit criteria:**
- EPK page views, play events, and outbound click-throughs captured
- Basic dashboard showing 30-day summary per artist
- No PII stored; no user accounts required

#### 4.1 Events Table

```sql
engagement_events (
  id UUID PRIMARY KEY,
  tenant_slug TEXT,
  event_type TEXT,   -- view|play|click|share|download
  target_type TEXT,  -- epk|gallery_item|outbound_link
  target_id TEXT,
  session_id TEXT,   -- anonymous cookie, no account required
  referrer TEXT,
  user_agent TEXT,
  created_at TIMESTAMPTZ
)

-- Index heavily:
-- (tenant_slug, event_type, created_at)
-- (target_id, event_type, created_at)
-- (created_at) for time-series
```

#### 4.2 Collection

- Lightweight JS beacon on EPK page for play/click events
- Server-side log on `GET /epk/public/{slug}` for page views
- No third-party analytics scripts in v1

#### 4.3 Reporting API (Internal)

- `GET /analytics/epk/summary?period=30d` — views, play count, CTR, top outbound links
- Data informs content decisions; does not drive automation yet
- Spotify/IG/TikTok API ingest: add later as separate ingest tables without touching `engagement_events`

---

### Phase 5 — Agentic Manager (scoped agent)

**Goal:** Maximally helpful agent with email, booking, strategy, and eventually transactions.

**Exit criteria:** TBD — design pass required before starting.

#### Scope

- In-process manager agent with whitelisted tools calling internal API (`promote`, `epk-public patch`, vision CRUD)
- Email inbox first; DMs / Telegram / Discord / texts queued behind it
- Agent can initiate gig bookings and email responses
- Biometric confirmation gate on any write transaction (design TBD)

#### Payments / Plaid

Read compliance docs at `docs/finance-compliance/` before any implementation. Read-only balance access first. Payments (invoices, ad spend, distro) require a dedicated design pass. Do not implement write access without biometric gate.

#### Agent architecture

Use a scoped in-process agent (OpenRouter + whitelisted backend tools). Expand tool surface deliberately; no external agent runtime with broad system access.

#### Metadata Design Pass (deferred from Phase 2)

Before agent work begins: design stable shapes for audio features, genre, BPM, rights, campaign tags. Move these out of JSONB and into typed columns where query patterns are known.

#### Video Self-Hosting / Decentralized Hosting

Research spike only. Blockchain-based video hosting has failed before (Dtube, etc.) but the space is evolving. Not on critical path. Keep `hero_video.type` schema extensible for a future `gallery` or `ipfs` type.

---

## 8. Deferred (Hard Boundary)

These are explicitly out of scope until called back in. Do not let them creep into Phases 1–3.

| Item | Status |
|---|---|
| Design Studio LLM layout | Frozen; EPK uses `booker_v1` slots only |
| Audience auto-tag on upload | Deferred; manual analysis only |
| `epk_config.design_*` fields | Deprecate gradually after `epk_public` ships |
| External public API (Zapier, scripts) | Internal only; design for openability but don't open |
| Plaid / payments | After compliance review and biometric gate design |
| Multi-channel inbox (DMs, Telegram, Discord) | Email first |
| Scoped agent tools | Whitelist-only; expand per channel (email, booking) with audit |
| Blockchain / decentralized video | Research spike; not on critical path |
| Spotify / IG / TikTok API ingest | Add as separate ingest tables in Phase 4+; don't touch core schema |
| Audience segmentation automation | Data only in Phase 4; no automated decisions |

---

## 9. Implementation Order

1. **Phase 1.1–1.3** — Storage paths, promote API, dual-read migration, EPK resolver update
2. **Phase 1.4–1.5** — Portal Workbench/Gallery tabs; seed script for first artist
3. **Phase 2** — Vision/timeline tables, lineage, `content_id` stability
4. **Phase 3** — Public EPK template + slot swap API + DNS config
5. **Phase 4** — Engagement events + basic dashboard
6. **Phase 5** — Manager email tools; payments when compliance ready

---

## 10. Success Metrics

- Zero `workbench/` objects served on public EPK URLs
- Promoting a track does not touch or delete the workbench master
- Replacing the EPK hero video is one API call, under 5 seconds perceived latency
- New artist goes from workbench upload → promote → EPK live without touching Design Studio
- Any URL ever published continues to resolve after a content update

---

## 11. Open Questions

Resolve before the relevant phase starts. Do not resolve informally — update this doc with the decision and rationale.

| # | Question | Resolve before | Status |
|---|---|---|---|
| 1 | Gallery staging ACL: presigned expiry window? Collaborator-shareable? | Phase 2 | Open |
| 2 | YouTube vs. gallery video in EPK v1: schema supports both, confirm YouTube-only for launch | Phase 3 | Open |
| 3 | Metadata stable shapes (BPM, genre, rights): when do JSONB fields get promoted to typed columns? | Phase 5 | Deferred |
| 4 | Biometric confirmation gate design for agent transactions | Phase 5 | Deferred |
| 5 | Agent tool whitelist: which write actions need artist confirmation? | Phase 5 | Deferred |