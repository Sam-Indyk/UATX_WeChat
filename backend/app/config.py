from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg://uatx:uatx_dev@localhost:5432/uatx_wechat"

    CLERK_JWKS_URL: str = ""
    CLERK_ISSUER: str = ""
    CLERK_AUDIENCE: str = ""

    # Empty = open to any domain (the documented production policy — see
    # CLAUDE.md). Override via the env var if you ever want to restrict;
    # the .env.example shows the format. Previously defaulted to
    # "student.uaustin.org", which silently locked prod out for accounts
    # that hadn't been issued a school email yet — the opposite of intent.
    ALLOWED_EMAIL_DOMAINS: str = ""
    APP_ENV: str = "dev"

    # Supabase Storage for listing photos. Leave empty to disable the
    # upload endpoint (returns 503). Service-role key required because
    # uploads go through the backend; the bucket is configured as public
    # for reads so we can stamp the resulting URL into listings.image_url.
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_STORAGE_BUCKET: str = "listing-images"

    # Stripe Connect for the marketplace checkout flow. Test mode is
    # fine for the demo (real card numbers never touch the app). Leave
    # empty to disable all Stripe endpoints (they return 503). The
    # webhook secret is generated when you create a webhook endpoint in
    # the Stripe dashboard, or via `stripe listen` in local dev.
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    # Where Stripe redirects buyers after they finish (or cancel) checkout.
    # In prod this is the Railway URL; locally it's the Vite dev server.
    STRIPE_RETURN_URL_BASE: str = "http://localhost:5173"
    # Cents per dollar the platform skims from each checkout (0-100).
    # 0 = no platform fee. The demo uses 0 — we're not collecting money.
    STRIPE_PLATFORM_FEE_BPS: int = 0

    @property
    def allowed_domains_list(self) -> list[str]:
        return [d.strip().lower() for d in self.ALLOWED_EMAIL_DOMAINS.split(",") if d.strip()]

    @property
    def stripe_enabled(self) -> bool:
        return bool(self.STRIPE_SECRET_KEY)


settings = Settings()
