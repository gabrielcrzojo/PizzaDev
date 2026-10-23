from datetime import datetime, timedelta, timezone
from typing import Literal

from jose import jwt
from passlib.context import CryptContext

from .config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# Mantém compatibilidade com o nome usado nas primeiras versões da aplicação.
bycript_context = bcrypt_context


def criar_token(
    id_usuario: int,
    duracao_token: timedelta | None = None,
    tipo_token: Literal["access", "refresh"] = "access",
) -> str:
    """Emite um JWT com validade e finalidade explícitas."""
    duracao = (
        duracao_token
        if duracao_token is not None
        else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    dados = {
        "sub": str(id_usuario),
        "exp": datetime.now(timezone.utc) + duracao,
        # Impede que um token de acesso seja usado para renovar a sessão.
        "type": tipo_token,
    }
    return jwt.encode(dados, SECRET_KEY, algorithm=ALGORITHM)
