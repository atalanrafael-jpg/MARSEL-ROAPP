from __future__ import annotations

import os

from .service import create_app


app = create_app(
    auth_token=os.getenv("COMPUTER_USE_RUNTIME_TOKEN", ""),
    allowed_origins=os.getenv("COMPUTER_USE_ALLOWED_ORIGINS", "").split(","),
    network_policy_enforced=os.getenv("COMPUTER_USE_NETWORK_POLICY_ENFORCED", "").lower() == "true",
)
