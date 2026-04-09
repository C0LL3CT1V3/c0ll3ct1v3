from pydantic_settings import BaseSettings


class Settings(BaseSettings):
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
    cors_origins: str = "http://localhost:3000"

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
    data_retention_raw_webhook_days: int = 90
    data_retention_app_log_days: int = 30
    data_retention_audit_log_days: int = 365

    class Config:
        env_file = ".env"


settings = Settings()
