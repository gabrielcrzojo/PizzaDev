from collections.abc import Generator
from typing import Annotated, Literal

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session, sessionmaker

from .config import ALGORITHM, SECRET_KEY
from .models import Usuario, db

SessionLocal = sessionmaker(bind=db)
# O Swagger envia um formulário OAuth2; o login JSON continua em /auth/login.
oauth2_schema = OAuth2PasswordBearer(tokenUrl="auth/login.form")


def pegar_sessao() -> Generator[Session, None, None]:
    """Entrega uma sessão por requisição e libera os recursos ao terminar."""
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def obter_usuario_token(
    token: str, session: Session, tipo_token: Literal["access", "refresh"]
) -> Usuario:
    """Valida assinatura, expiração, finalidade e situação atual do usuário."""
    erro_token = HTTPException(
        status_code=401,
        detail="Token inválido ou expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        dados = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"require_exp": True, "require_sub": True},
        )
        if dados.get("type") != tipo_token:
            raise erro_token
        id_usuario = int(dados["sub"])
        if id_usuario <= 0:
            raise erro_token
    except (JWTError, ValueError, TypeError) as exc:
        raise erro_token from exc

    usuario = session.get(Usuario, id_usuario)
    if usuario is None:
        raise erro_token
    if not usuario.ativo:
        raise HTTPException(status_code=403, detail="Usuário inativo")
    return usuario


def verificar_token(
    token: Annotated[str, Depends(oauth2_schema)],
    session: Annotated[Session, Depends(pegar_sessao)],
) -> Usuario:
    return obter_usuario_token(token, session, "access")


def verificar_refresh_token(
    token: Annotated[str, Depends(oauth2_schema)],
    session: Annotated[Session, Depends(pegar_sessao)],
) -> Usuario:
    return obter_usuario_token(token, session, "refresh")


def verificar_admin(
    usuario: Annotated[Usuario, Depends(verificar_token)],
) -> Usuario:
    if not usuario.admin:
        raise HTTPException(
            status_code=403, detail="Operação exclusiva de administradores"
        )
    return usuario
