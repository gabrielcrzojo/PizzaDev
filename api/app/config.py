import os
from pathlib import Path

from dotenv import load_dotenv

API_DIR = Path(__file__).resolve().parent.parent
load_dotenv(API_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
# Converte a configuração com uma mensagem útil em caso de valor inválido.
try:
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
except ValueError as exc:
    raise RuntimeError(
        "ACCESS_TOKEN_EXPIRE_MINUTES deve ser um número inteiro."
    ) from exc
DATABASE_URL = os.getenv(
    "DATABASE_URL", f"sqlite:///{(API_DIR / 'banco.db').as_posix()}"
)
CORS_ORIGINS = [
    x.strip() for x in os.getenv("CORS_ORIGINS", "").split(",") if x.strip()
]

# Falhas de configuração devem aparecer antes de emitir tokens.
if not SECRET_KEY or not SECRET_KEY.strip():
    raise RuntimeError("Configure SECRET_KEY no arquivo api/.env.")
if ALGORITHM not in {"HS256", "HS384", "HS512"}:
    raise RuntimeError("ALGORITHM deve ser HS256, HS384 ou HS512.")
if ACCESS_TOKEN_EXPIRE_MINUTES <= 0:
    raise RuntimeError("ACCESS_TOKEN_EXPIRE_MINUTES deve ser maior que zero.")
