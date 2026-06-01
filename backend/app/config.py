from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg://uatx:uatx_dev@localhost:5432/uatx_wechat"

    CLERK_JWKS_URL: str = ""
    CLERK_ISSUER: str = ""
    CLERK_AUDIENCE: str = ""

    ALLOWED_EMAIL_DOMAINS: str = "student.uaustin.org"
    APP_ENV: str = "dev"

    # Supabase Storage for listing photos. Leave empty to disable the
    # upload endpoint (returns 503). Service-role key required because
    # uploads go through the backend; the bucket is configured as public
    # for reads so we can stamp the resulting URL into listings.image_url.
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_STORAGE_BUCKET: str = "listing-images"

    @property
    def allowed_domains_list(self) -> list[str]:
        return [d.strip().lower() for d in self.ALLOWED_EMAIL_DOMAINS.split(",") if d.strip()]


settings = Settings()
