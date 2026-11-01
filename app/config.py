from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    roapp_base_url: str = "https://api.roapp.io/v2"
    roapp_api_key: str = ""
    roapp_timeout_seconds: float = 30
    roapp_max_requests_per_second: int = 3
    roapp_max_retries: int = 3
    roapp_retry_base_seconds: float = 0.75

    # Protects the connector's RO App proxy/audit endpoints.
    # This is deliberately separate from ROAPP_API_KEY: the former authorizes
    # callers to MARSEL ROAPP, while the latter authenticates MARSEL to RO App.
    marsel_internal_api_key: str = ""

    # Automation mode: fail-closed / read-only by default
    automation_mode_enabled: bool = False
    automation_mode_name: str = "READ_ONLY"
    automation_allow_write: bool = False
    automation_allow_external_calls: bool = False
    automation_max_actions_per_run: int = 1
    automation_require_evidence: bool = True
    automation_require_approval: bool = True

    # OpenAI Ads Conversions API credentials must come from Ads Manager > Conversions.
    # Never use the general OpenAI Platform API key for this integration.
    openai_ads_pixel_id: str = ""
    openai_ads_conversions_api_key: str = ""
    openai_ads_base_url: str = "https://bzr.openai.com"
    openai_ads_validate_only: bool = False
    openai_ads_integration_source: str = "marsel_roapp"
    openai_ads_default_currency: str = "RUB"
    openai_ads_source_url: str = ""
    openai_ads_timeout_seconds: int = 15

    # Gmail read-only OAuth integration.
    # Credentials are supplied through environment variables; no secret is stored here.
    gmail_account_email: str = ""

    # MCP / ChatGPT / Codex integration.
    # HTTP mode is disabled by default so existing deployments remain unchanged.
    # Enable HTTP mode only with a real OAuth 2.1/OIDC issuer and HTTPS resource URL.
    mcp_http_enabled: bool = False
    mcp_resource_server_url: str = ""
    mcp_auth_issuer: str = ""
    mcp_auth_jwks_url: str = ""
    mcp_required_scopes: list[str] = Field(default_factory=list)
    supabase_url: str = "https://wdbytmvzuensuuoquvav.supabase.co"
    supabase_publishable_key: str = ""

    # Premium AI layer; server-side only.
    openai_api_key: str = ""
    openai_model: str = "gpt-6-luna"

    # OpenAI Responses API Computer Use. Disabled until a separately isolated
    # runtime is configured, authenticated, and confirms enforcement of policy.
    openai_computer_use_model: str = "gpt-6-astra"
    computer_use_enabled: bool = False
    computer_use_runtime_url: str = ""
    computer_use_runtime_token: str = ""
    computer_use_allowed_origins: list[str] = Field(default_factory=list)
    computer_use_runtime_timeout_seconds: int = 45
    computer_use_max_turns: int = 8
    computer_use_max_code_chars: int = 20000
    computer_use_max_output_images: int = 4

    # Premium payments; live charging is fail-closed by default.
    payment_provider: str = "yookassa"
    payment_shop_id: str = ""
    payment_secret_key: str = ""
    payment_return_url: str = ""
    payment_live_enabled: bool = False
    payment_timeout_seconds: int = 20

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
