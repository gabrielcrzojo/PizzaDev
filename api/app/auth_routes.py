from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from passlib.exc import UnknownHashError
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .dependencies import pegar_sessao, verificar_refresh_token, verificar_token
from .models import Usuario
from .schemas import (
    LoginSchema,
    LoginTokenSchema,
    PerfilSchema,
    TokenSchema,
    UsuarioResposta,
    UsuarioSchema,
)
from .security import bcrypt_context, criar_token

auth_router = APIRouter(prefix="/auth", tags=["auth"])


def autenticar_usuario(email: str, senha: str, session: Session) -> Usuario:
    """Compartilha a autenticação entre o login JSON e o formulário do Swagger."""
    usuario = (
        session.query(Usuario)
        .filter(func.lower(Usuario.email) == email.strip().lower())
        .first()
    )
    senha_valida = False
    if usuario is not None and len(senha.encode("utf-8")) <= 72:
        try:
            senha_valida = bcrypt_context.verify(senha, usuario.senha)
        except (ValueError, UnknownHashError):
            # Um hash legado inválido não deve transformar o login em erro 500.
            senha_valida = False

    if not senha_valida:
        raise HTTPException(
            status_code=401,
            detail="Email não encontrado ou senha incorreta",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not usuario.ativo:
        raise HTTPException(status_code=403, detail="Usuário inativo")
    return usuario


@auth_router.get("/")
def autenticar():
    """Mantém o endpoint público de disponibilidade da autenticação."""
    return {"message": "Autenticação bem-sucedida!"}


@auth_router.post("/criar_conta")
def criar_conta(
    usuario_schema: UsuarioSchema,
    session: Annotated[Session, Depends(pegar_sessao)],
):
    usuario = (
        session.query(Usuario)
        .filter(func.lower(Usuario.email) == usuario_schema.email)
        .first()
    )
    if usuario:
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    novo_usuario = Usuario(
        nome=usuario_schema.nome,
        email=usuario_schema.email,
        senha=bcrypt_context.hash(usuario_schema.senha),
        ativo=True,
        admin=False,
    )
    session.add(novo_usuario)
    try:
        session.commit()
    except IntegrityError as exc:
        # A restrição UNIQUE também protege cadastros simultâneos do mesmo email.
        session.rollback()
        raise HTTPException(status_code=400, detail="Email já cadastrado") from exc

    return {"message": f"Conta criada com sucesso! {usuario_schema.email}"}


@auth_router.post("/login", response_model=LoginTokenSchema)
def login(
    login_schema: LoginSchema,
    session: Annotated[Session, Depends(pegar_sessao)],
):
    usuario = autenticar_usuario(login_schema.email, login_schema.senha, session)
    return {
        "access_token": criar_token(usuario.id),
        "refresh_token": criar_token(
            usuario.id, duracao_token=timedelta(days=7), tipo_token="refresh"
        ),
        "token_type": "Bearer",
    }


@auth_router.post("/login.form", response_model=TokenSchema)
def login_form(
    dados_formulario: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[Session, Depends(pegar_sessao)],
):
    # No formulário OAuth2, o campo username recebe o email do usuário.
    usuario = autenticar_usuario(
        dados_formulario.username, dados_formulario.password, session
    )
    return {"access_token": criar_token(usuario.id), "token_type": "Bearer"}


@auth_router.post("/refresh", response_model=TokenSchema)
def use_refresh_token(
    usuario: Annotated[Usuario, Depends(verificar_refresh_token)],
):
    """Recebe o refresh token no cabeçalho Authorization: Bearer <token>."""
    return {"access_token": criar_token(usuario.id), "token_type": "Bearer"}


@auth_router.get("/me", response_model=UsuarioResposta)
def consultar_perfil(usuario: Annotated[Usuario, Depends(verificar_token)]):
    return usuario


@auth_router.patch("/me", response_model=UsuarioResposta)
def atualizar_perfil(
    dados: PerfilSchema,
    usuario: Annotated[Usuario, Depends(verificar_token)],
    session: Annotated[Session, Depends(pegar_sessao)],
):
    usuario.nome = dados.nome
    session.commit()
    session.refresh(usuario)
    return usuario
