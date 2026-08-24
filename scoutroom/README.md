# Scoutroom

Working name for a Rails 8 social-prediction app: fans stake **virtual points** on indie-artist milestones. Early / contrarian / correct calls earn more of the losing **points** pool. Real money is a Stripe **tip to the artist** and never moves with a call.

Points have no cash value. UI copy says *call* and *points*, not odds or bets.

## Run locally

Postgres and Redis (already used by this repo's Compose stack can stay up; Scoutroom uses its own containers on **5434** / **6380**):

```bash
cd scoutroom
docker compose up -d
bin/setup   # or: bin/rails db:prepare db:seed
bin/dev     # web :3000, Tailwind, Sidekiq
```

Need Ruby 3.3 (this folder has `mise.toml`). First-time: `mise install`.

- App: http://localhost:3000
- Seed admin: `admin@scoutroom.test` / `password123` (also `scout`, `mica`, `juniper`)
- Instagram mock: http://localhost:3000/dev/ig
- Sidekiq: http://localhost:3000/sidekiq

## What is in v1

- Devise auth, points ledger, one call per user per market
- `Markets::PriceEngine` (seeded pool, entry-price weights, unit tests)
- Admin resolve → Sidekiq payouts / void refunds
- Generative SVG slips (1080×1920), leaderboard, profiles, badges
- Stripe tips namespace (Connect destination charges when keys + `stripe_account_id` exist)
- Instagram comment-to-DM **mocked** until Meta review

## Tests

```bash
cd scoutroom
bin/rails test
```
