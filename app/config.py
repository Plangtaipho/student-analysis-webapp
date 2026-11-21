"""Application settings, read from environment variables (or a local .env file)."""
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # "development" or "production". Production turns on secure cookies and hides API docs.
    env: str = "development"

    # SQLAlchemy URL. Local default is SQLite; production uses MySQL, e.g.
    # mysql+pymysql://user:password@host:3306/student_analysis
    database_url: str = "sqlite:///./dev.db"

    # Path to a CA certificate for TLS connections to a managed MySQL service (optional).
    db_ssl_ca: str = ""

    # Long random string used to sign session cookies. MUST be set in production.
    secret_key: str = "dev-only-change-me"

    # Public address of the site, used in student links and QR codes,
    # e.g. https://example.com . Empty = use the address of the current request.
    public_base_url: str = ""

    session_max_age_hours: int = 12
    timezone: str = "Asia/Bangkok"

    # When no admin exists at startup, one is created from these values.
    initial_admin_email: str = ""
    initial_admin_password: str = ""

    # Price of one semester (all classrooms of that term), in baht.
    price_per_term: int = 129
    # PromptPay receiver: a mobile number (0812345678) or a 13-digit ID. Empty = QR not shown.
    promptpay_id: str = ""
    # Account name shown to teachers before they transfer, e.g. "นางสาว... (KruFlow)".
    promptpay_name: str = ""

    # "Sign in with Google". Both empty = the Google button is hidden.
    # Create an OAuth client (type: Web application) at console.cloud.google.com.
    google_client_id: str = ""
    google_client_secret: str = ""

    # Delete classrooms 45 days after their semester ends (see app/services/retention.py).
    retention_enabled: bool = True

    @field_validator("public_base_url", "env", "promptpay_id", "promptpay_name", "initial_admin_email", mode="before")
    @classmethod
    def _trim(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator("public_base_url")
    @classmethod
    def _with_scheme(cls, v: str) -> str:
        # "example.up.railway.app" (no https://) would make student links relative and broken.
        v = v.rstrip("/")
        if v and not v.startswith(("http://", "https://")):
            v = "https://" + v
        return v

    @property
    def google_enabled(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def is_production(self) -> bool:
        return self.env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
