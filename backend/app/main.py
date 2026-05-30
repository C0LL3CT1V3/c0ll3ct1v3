from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from .api.accounts import router as accounts_router
from .api.auth import router as auth_router
from .api.artists.router import router as artists_router
from .api.epk.router import router as epk_router
from .api.epk.design_router import router as epk_design_router
from .api.manager.router import router as manager_router
from .api.media.router import router as media_router
from .api.music.router import router as music_router
from .config import settings
from .database import Base, engine
from .models import account, artist, document, ledger, media, user, wallet

from .finance_integrations.router import router as finance_router
from .finance_integrations.validation import validate_finance_production_config

app = FastAPI(title="C0ll3CT1V3 Business Management System", version="1.0.0")

# CORS middleware — apex portal origins + regex for artist EPK subdomains (*.localhost dev, *.c0ll3ct1v3.xyz prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list(),
    allow_origin_regex="|".join(settings.cors_origin_regex_list()),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(accounts_router)
app.include_router(auth_router)
app.include_router(media_router)
app.include_router(artists_router)
app.include_router(manager_router)
app.include_router(epk_router)
app.include_router(epk_design_router)
app.include_router(music_router)
if settings.finance_integrations_enabled:
    app.include_router(finance_router)

Base.metadata.create_all(bind=engine)


def _seed_default_artist() -> None:
    """Ensure the primary tenant has a public EPK profile before first login."""
    from .config import settings
    from .database import SessionLocal
    from .models.artist import Artist, default_epk_config

    slug = settings.default_media_tenant_slug.strip().lower()
    db = SessionLocal()
    try:
        if db.query(Artist).filter(Artist.tenant_slug == slug).first():
            return
        cfg = default_epk_config()
        cfg.update(
            {
                "tagline": "Composer · Performer",
                "bio": "Independent artist on c0ll3ct1v3.",
                "booking_email": "booking@phillipjames.com",
            }
        )
        db.add(
            Artist(
                auth0_sub=f"seed:{slug}",
                tenant_slug=slug,
                display_name="Phillip James",
                epk_config=cfg,
            )
        )
        db.commit()
    finally:
        db.close()


_seed_default_artist()


def _run_schema_migrations() -> None:
    """Apply additive schema migrations needed for Auth0 rollout."""
    inspector = inspect(engine)
    users_columns = {column["name"] for column in inspector.get_columns("users")}
    account_columns = {column["name"] for column in inspector.get_columns("bank_accounts")}

    with engine.begin() as connection:
        if "auth0_sub" not in users_columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN auth0_sub VARCHAR"))
        if "email_verified" not in users_columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT FALSE"))
        if "onboarding_completed" not in users_columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN onboarding_completed BOOLEAN DEFAULT FALSE"))
        connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_auth0_sub ON users (auth0_sub)"))

        if "user_id" not in account_columns:
            first_user_id = connection.execute(text("SELECT id FROM users ORDER BY id LIMIT 1")).scalar()
            if first_user_id is None:
                connection.execute(
                    text(
                        "INSERT INTO users (name, email, hashed_password, is_active, email_verified, onboarding_completed) "
                        "VALUES (:name, :email, :hashed_password, TRUE, FALSE, FALSE)"
                    ),
                    {
                        "name": "Legacy Owner",
                        "email": "legacy-owner@local.invalid",
                        "hashed_password": "legacy-migrated-disabled",
                    },
                )
                first_user_id = connection.execute(text("SELECT id FROM users ORDER BY id LIMIT 1")).scalar()

            connection.execute(text("ALTER TABLE bank_accounts ADD COLUMN user_id INTEGER"))
            connection.execute(
                text("UPDATE bank_accounts SET user_id = :owner WHERE user_id IS NULL"),
                {"owner": int(first_user_id)},
            )
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_bank_accounts_user_id ON bank_accounts (user_id)"))


_run_schema_migrations()

@app.on_event("startup")
def _validate_finance_production_config() -> None:
    if not settings.finance_integrations_enabled:
        return
    errors = validate_finance_production_config()
    if errors:
        raise RuntimeError("Finance production configuration invalid: " + "; ".join(errors))


@app.get("/")
async def root():
    return {"message": "C0ll3CT1V3 Business Management SystemAPI"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
