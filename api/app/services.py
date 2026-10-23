"""Regras compartilhadas pelos endpoints de pedidos e administração."""

from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import ItemPedido, Pedido, Usuario


def obter_pedido(session: Session, pedido_id: int, usuario: Usuario) -> Pedido:
    pedido = session.get(Pedido, pedido_id)
    if pedido is None:
        raise HTTPException(404, "Pedido não encontrado")
    if pedido.usuario != usuario.id and not usuario.admin:
        raise HTTPException(403, "Acesso ao pedido não permitido")
    return pedido


def exigir_pendente(pedido: Pedido) -> None:
    if pedido.status != "PENDENTE":
        raise HTTPException(409, "Somente pedidos pendentes podem ser alterados")


def recalcular_total(session: Session, pedido: Pedido) -> None:
    # Flush inclui inclusões/exclusões ainda não confirmadas na mesma transação.
    session.flush()
    itens = session.scalars(select(ItemPedido).where(ItemPedido.pedido == pedido.id))
    pedido.preco = sum(
        (Decimal(str(item.preco_unitario)) * item.quantidade for item in itens),
        Decimal("0.00"),
    )
    if pedido.preco > Decimal("9999999999.99"):
        raise HTTPException(422, "O total excede o limite monetário do pedido")
    # A versão também muda quando apenas um item é alterado; impede totais perdidos
    # em duas atualizações concorrentes do mesmo pedido.
    pedido.versao += 1
