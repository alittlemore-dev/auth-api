import hashlib
import secrets
from dataclasses import dataclass

from core.schemas import Secret


@dataclass(frozen=True, slots=True)
class ApiTokenSecretGenerator:
    def generate(self) -> Secret[str]:
        return Secret("alm_pat_" + secrets.token_urlsafe(32))

    def hash_secret(self, *, secret: Secret[str]) -> str:
        return hashlib.sha256(secret.get_secret_value().encode()).hexdigest()
