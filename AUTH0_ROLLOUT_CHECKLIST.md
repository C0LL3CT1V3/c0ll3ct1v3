# Auth0 Rollout Checklist

## Stage 1: Configure Auth0 and environments

- Set backend env from `backend/.env.example`.
- Set frontend env from `frontend/.env.example`.
- Install dependencies:
  - `pip install -r backend/requirements.txt`
  - `npm install` in `frontend/`

## Stage 2: Validate onboarding cutover

- Confirm `ENABLE_LEGACY_PASSWORD_AUTH=false`.
- Login via Auth0 and call `GET /auth/session`.
- Verify first login auto-provisions local user.
- Verify existing local user with matching email gets `auth0_sub` bound.

## Stage 3: Validate API authorization and ownership

- Ensure unauthenticated call to `GET /accounts/` returns 401.
- Ensure one user cannot view another user's account rows.
- Ensure account create requires valid access token and recent MFA.

## Stage 4: Validate MFA step-up

- Trigger sensitive action (`POST /accounts/`) with token lacking MFA; expect `403 mfa_required`.
- Trigger Auth0 step-up and retry action; confirm request succeeds.

## Stage 5: Legacy endpoint deprecation

- Verify `/auth/register` and `/auth/login` return 410 while legacy auth disabled.
- Keep rollback option by setting `ENABLE_LEGACY_PASSWORD_AUTH=true` only for emergency transition.

