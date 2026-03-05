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
    
    class Config:
        env_file = ".env"

settings = Settings()
