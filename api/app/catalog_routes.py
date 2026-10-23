"""Catálogo público; alterações exigem uma conta administrativa."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .dependencies import pegar_sessao, verificar_admin
from .models import Produto, Usuario
from .schemas import ProdutoResposta, ProdutoSchema

catalog_router = APIRouter(prefix="/products", tags=["catálogo"])
Sessao = Annotated[Session, Depends(pegar_sessao)]
Admin = Annotated[Usuario, Depends(verificar_admin)]


@catalog_router.get("/", response_model=list[ProdutoResposta])
def listar_produtos(
    session: Sessao,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return session.scalars(
        select(Produto)
        .where(Produto.ativo.is_(True))
        .order_by(Produto.id)
        .offset(offset)
        .limit(limit)
    ).all()


@catalog_router.get("/admin", response_model=list[ProdutoResposta])
def listar_catalogo_admin(
    session: Sessao,
    admin: Admin,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return session.scalars(
        select(Produto).order_by(Produto.id).offset(offset).limit(limit)
    ).all()


def obter_produto(session: Session, produto_id: int) -> Produto:
    produto = session.get(Produto, produto_id)
    if produto is None:
        raise HTTPException(404, "Produto não encontrado")
    return produto


@catalog_router.get("/{produto_id}", response_model=ProdutoResposta)
def consultar_produto(produto_id: int, session: Sessao):
    produto = obter_produto(session, produto_id)
    if not produto.ativo:
        raise HTTPException(404, "Produto não encontrado")
    return produto


@catalog_router.post("/", response_model=ProdutoResposta, status_code=201)
def criar_produto(dados: ProdutoSchema, session: Sessao, admin: Admin):
    produto = Produto(**dados.model_dump())
    session.add(produto)
    session.commit()
    session.refresh(produto)
    return produto


@catalog_router.put("/{produto_id}", response_model=ProdutoResposta)
def atualizar_produto(
    produto_id: int, dados: ProdutoSchema, session: Sessao, admin: Admin
):
    produto = obter_produto(session, produto_id)
    for campo, valor in dados.model_dump().items():
        setattr(produto, campo, valor)
    session.commit()
    session.refresh(produto)
    return produto


@catalog_router.delete("/{produto_id}", status_code=204)
def desativar_produto(produto_id: int, session: Sessao, admin: Admin):
    # Exclusão lógica preserva referências e histórico dos pedidos.
    produto = obter_produto(session, produto_id)
    produto.ativo = False
    session.commit()
    return Response(status_code=204)
