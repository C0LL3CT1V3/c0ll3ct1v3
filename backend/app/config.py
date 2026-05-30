from pydantic_settings import BaseSettings, SettingsConfigDict


# Always merged when APP_ENV=development so a stale .env (port 3000 only) does not break SPA on :3030.
_DEV_BROWSER_ORIGINS = (
    "http://localhost:3000",
    "http://localhost:3030",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3030",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./collective.db"
    secret_key: str = "deprecated-legacy-secret-not-used-in-auth0-mode"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    enable_legacy_password_auth: bool = False

    auth_provider: str = "auth0"
    auth0_domain: str = ""
    auth0_audience: str = ""
    auth0_issuer: str = ""
    auth0_algorithms: str = "RS256"
    mfa_required: bool = True
    mfa_max_age_seconds: int = 900
    # Comma-separated; include SPA dev ports used by docker-compose / README
    cors_origins: str = (
        "http://localhost:3000,"
        "http://localhost:3030,"
        "http://127.0.0.1:3000,"
        "http://127.0.0.1:3030"
    )

    # --- Plaid / Square finance integrations (optional; see docs/finance-compliance) ---
    app_env: str = "development"
    finance_integrations_enabled: bool = True
    finance_demo_auth: bool = False
    finance_mfa_consumer_enforced: bool = False
    finance_mfa_step_up_for_plaid_link: bool = False
    finance_mfa_methods_allowed: str = "totp,webauthn"
    finance_mfa_demo_otp: str = "123456"
    finance_mfa_admin_enforced: bool = True

    plaid_env: str = "sandbox"
    plaid_client_id: str = ""
    plaid_secret: str = ""
    plaid_webhook_url: str = ""
    plaid_products: str = "transactions,accounts"
    plaid_country_codes: str = "US"
    plaid_link_mode: str = "stub"
    plaid_webhook_secret: str = ""

    square_env: str = "sandbox"
    square_base_url: str = "https://connect.squareupsandbox.com/v2"
    square_access_token: str = ""
    square_application_id: str = ""
    square_application_secret: str = ""
    square_webhook_signature_key: str = ""
    square_webhook_url: str = ""

    encryption_key_id: str = ""
    redact_log_secrets: bool = True

    # Creative media — DigitalOcean Spaces (S3-compatible) or MinIO
    spaces_enabled: bool = False
    spaces_endpoint: str = ""  # e.g. https://nyc3.digitaloceanspaces.com
    spaces_region: str = "nyc3"
    spaces_bucket: str = "pj-media"
    spaces_access_key: str = ""
    spaces_secret_key: str = ""
    spaces_public_endpoint: str = ""  # Browser-facing endpoint for presigned URLs (e.g. http://localhost:9000)
    media_cdn_base_url: str = ""  # Spaces CDN endpoint; omit to build from bucket + endpoint
    default_media_tenant_slug: str = "phillipjames"
    # Comma-separated. If user's email matches a marker, bind Auth0 → default tenant seed row instead of slug-2 spillover.
    primary_artist_claim_email_markers: str = "phillip,phillipjames.com"
    # Optional exact Auth0 subjects (comma-separated) that may claim the seeded default tenant workspace.
    primary_artist_claim_auth0_subs: str = ""
    media_multipart_chunk_bytes: int = 8388608  # 8 MiB parts
    media_max_upload_bytes: int = 5368709120  # 5 GiB masters
    media_presigned_upload_expires_seconds: int = 3600
    media_presigned_download_expires_seconds: int = 900

    redis_url: str = ""  # e.g. redis://redis:6379/0 for worker queue

    # Audience mapper (Spotify Client Credentials + librosa)
    audience_analysis_enabled: bool = True
    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    lastfm_api_key: str = ""
    data_retention_raw_webhook_days: int = 90
    data_retention_app_log_days: int = 30
    data_retention_audit_log_days: int = 365

    def cors_origin_list(self) -> list[str]:
        merged: list[str] = []
        for origin in self.cors_origins.split(","):
            o = origin.strip()
            if o and o not in merged:
                merged.append(o)
        if self.app_env == "development":
            for o in _DEV_BROWSER_ORIGINS:
                if o not in merged:
                    merged.append(o)
        return merged

    def cors_origin_regex_list(self) -> list[str]:
        """Regex patterns for artist EPK subdomains (public SPA, no credentials on EPK)."""
        patterns: list[str] = []
        if self.app_env == "development":
            # http://phillipjames.localhost:3030 and any other *.localhost dev EPK host
            patterns.append(r"https?://[\w][\w-]*\.localhost(:\d+)?$")
        # Production artist sites: https://{slug}.c0ll3ct1v3.xyz
        patterns.append(r"https://[\w][\w-]*\.c0ll3ct1v3\.xyz$")
        return patterns


settings = Settings()
