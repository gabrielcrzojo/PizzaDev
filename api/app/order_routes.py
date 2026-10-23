from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .dependencies import pegar_sessao, verificar_admin, verificar_token
from .models import ItemPedido, Pedido, Produto, Usuario
from .schemas import (
    ItemPedidoSchema,
    PedidoCriadoResposta,
    PedidoResposta,
    PedidoSchema,
    QuantidadeSchema,
    StatusPedido,
    StatusSchema,
)
from .services import exigir_pendente, obter_pedido, recalcular_total

Sessao = Annotated[Session, Depends(pegar_sessao)]
Autenticado = Annotated[Usuario, Depends(verificar_token)]
Admin = Annotated[Usuario, Depends(verificar_admin)]

order_router = APIRouter(prefix="/orders", tags=["orders"])


@order_router.get("/")
def pedidos():
    """Mantém o endpoint público de disponibilidade do serviço de pedidos."""
    return {"message": "Pedidos bem-sucedidos!"}


@order_router.post("/pedido", response_model=PedidoCriadoResposta)
def criar_pedido(
    pedido_schema: PedidoSchema,
    session: Annotated[Session, Depends(pegar_sessao)],
    usuario: Annotated[Usuario, Depends(verificar_token)],
):
    # Mantém o campo usuario do contrato atual, validando quem pode usá-lo.
    if pedido_schema.usuario != usuario.id and not usuario.admin:
        raise HTTPException(
            status_code=403, detail="Não é permitido criar pedidos para outro usuário"
        )
    destinatario = session.get(Usuario, pedido_schema.usuario)
    if destinatario is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if not destinatario.ativo:
        raise HTTPException(status_code=403, detail="Usuário inativo")

    # Pedidos começam vazios; os itens determinam o total no servidor.
    novo_pedido = Pedido(usuario=destinatario.id)
    session.add(novo_pedido)
    try:
        session.commit()
        session.refresh(novo_pedido)
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=409, detail="Não foi possível criar o pedido"
        ) from exc
    return {
        "message": f"Pedido criado com sucesso!, ID: {novo_pedido.id}",
        "id": novo_pedido.id,
    }


@order_router.get("/listar", response_model=list[PedidoResposta])
def listar_pedidos(
    session: Sessao,
    usuario: Autenticado,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    status: StatusPedido | None = None,
):
    consulta = select(Pedido)
    if not usuario.admin:
        consulta = consulta.where(Pedido.usuario == usuario.id)
    if status:
        consulta = consulta.where(Pedido.status == status)
    return session.scalars(
        consulta.order_by(Pedido.id.desc()).offset(offset).limit(limit)
    ).all()


@order_router.get("/listar/pedidos-usuario", response_model=list[PedidoResposta])
def meus_pedidos(
    session: Sessao,
    usuario: Autenticado,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return session.scalars(
        select(Pedido)
        .where(Pedido.usuario == usuario.id)
        .order_by(Pedido.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()


@order_router.get("/pedido/{id_pedido}", response_model=PedidoResposta)
def visualizar_pedido(id_pedido: int, session: Sessao, usuario: Autenticado):
    return obter_pedido(session, id_pedido, usuario)


@order_router.post("/pedido/adicionar-item/{id_pedido}", response_model=PedidoResposta)
def adicionar_item(
    id_pedido: int,
    dados: ItemPedidoSchema,
    session: Sessao,
    usuario: Autenticado,
):
    pedido = obter_pedido(session, id_pedido, usuario)
    exigir_pendente(pedido)
    produto = session.get(Produto, dados.produto_id)
    if produto is None or not produto.ativo:
        raise HTTPException(404, "Produto indisponível")
    # Preço e descrição são fotografados no servidor. Mudanças no catálogo não
    # reescrevem pedidos existentes, e o cliente nunca define o próprio preço.
    session.add(
        ItemPedido(
            quantidade=dados.quantidade,
            sabor=produto.sabor,
            tamanho=produto.tamanho,
            preco_unitario=produto.preco,
            pedido=pedido.id,
            produto_id=produto.id,
        )
    )
    recalcular_total(session, pedido)
    session.commit()
    session.refresh(pedido)
    return pedido


def obter_item(session: Session, pedido: Pedido, item_id: int) -> ItemPedido:
    item = session.get(ItemPedido, item_id)
    if item is None or item.pedido != pedido.id:
        raise HTTPException(404, "Item não encontrado neste pedido")
    return item


@order_router.patch(
    "/pedido/{id_pedido}/itens/{id_item}", response_model=PedidoResposta
)
def alterar_quantidade(
    id_pedido: int,
    id_item: int,
    dados: QuantidadeSchema,
    session: Sessao,
    usuario: Autenticado,
):
    pedido = obter_pedido(session, id_pedido, usuario)
    exigir_pendente(pedido)
    item = obter_item(session, pedido, id_item)
    item.quantidade = dados.quantidade
    recalcular_total(session, pedido)
    session.commit()
    session.refresh(pedido)
    return pedido


@order_router.delete("/pedido/remover-item/{id_item}", response_model=PedidoResposta)
def remover_item(id_item: int, session: Sessao, usuario: Autenticado):
    item = session.get(ItemPedido, id_item)
    if item is None:
        raise HTTPException(404, "Item não encontrado")
    pedido = obter_pedido(session, item.pedido, usuario)
    exigir_pendente(pedido)
    session.delete(item)
    recalcular_total(session, pedido)
    session.commit()
    session.refresh(pedido)
    return pedido


@order_router.post("/pedido/finalizar/{id_pedido}", response_model=PedidoResposta)
def finalizar_pedido(id_pedido: int, session: Sessao, usuario: Autenticado):
    pedido = obter_pedido(session, id_pedido, usuario)
    exigir_pendente(pedido)
    if not pedido.itens:
        raise HTTPException(409, "Adicione pelo menos um item antes de finalizar")
    pedido.status = "FINALIZADO"
    session.commit()
    session.refresh(pedido)
    return pedido


@order_router.post("/pedido/cancelar/{id_pedido}", response_model=PedidoResposta)
def cancelar_pedido(id_pedido: int, session: Sessao, usuario: Autenticado):
    pedido = obter_pedido(session, id_pedido, usuario)
    if pedido.status not in {"PENDENTE", "FINALIZADO"}:
        raise HTTPException(409, "O pedido não pode mais ser cancelado")
    pedido.status = "CANCELADO"
    session.commit()
    session.refresh(pedido)
    return pedido


@order_router.patch("/pedido/{id_pedido}/status", response_model=PedidoResposta)
def atualizar_status(
    id_pedido: int, dados: StatusSchema, session: Sessao, admin: Admin
):
    pedido = obter_pedido(session, id_pedido, admin)
    transicoes = {
        "FINALIZADO": {"PREPARANDO", "CANCELADO"},
        "PREPARANDO": {"EM_ENTREGA", "CANCELADO"},
        "EM_ENTREGA": {"ENTREGUE"},
    }
    if dados.status not in transicoes.get(pedido.status, set()):
        raise HTTPException(409, "Transição de status não permitida")
    pedido.status = dados.status
    session.commit()
    session.refresh(pedido)
    return pedido
