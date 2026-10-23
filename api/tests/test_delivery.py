"""Aceitação dos fluxos completos de catálogo e pedidos via HTTP."""

import unittest
from decimal import Decimal

import test_api
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.models import ItemPedido, Pedido


class DeliveryTestCase(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = test_api.APITestCase.asyncSetUp
    asyncTearDown = test_api.APITestCase.asyncTearDown
    autorizacao = test_api.APITestCase.autorizacao

    async def criar_produto(self, preco="19.90"):
        response = await self.client.post(
            "/products/",
            headers=self.autorizacao(3),
            json={"nome": "Pizza", "sabor": "Queijo", "tamanho": "M", "preco": preco},
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["id"]

    async def criar_pedido(self, usuario=1):
        response = await self.client.post(
            "/orders/pedido",
            headers=self.autorizacao(usuario),
            json={"usuario": usuario},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["id"]

    async def adicionar(self, pedido, produto, quantidade=2, usuario=1):
        return await self.client.post(
            f"/orders/pedido/adicionar-item/{pedido}",
            headers=self.autorizacao(usuario),
            json={"produto_id": produto, "quantidade": quantidade},
        )

    async def test_fluxo_completo_sem_pagamento(self):
        produto = await self.criar_produto()
        pedido = await self.criar_pedido()
        response = await self.adicionar(pedido, produto)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["preco"], "39.80")
        item = response.json()["itens"][0]["id"]
        response = await self.client.patch(
            f"/orders/pedido/{pedido}/itens/{item}",
            headers=self.autorizacao(),
            json={"quantidade": 3},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["preco"], "59.70")
        response = await self.client.post(
            f"/orders/pedido/finalizar/{pedido}",
            headers=self.autorizacao(),
        )
        self.assertEqual(response.json()["status"], "FINALIZADO")
        for status in ("PREPARANDO", "EM_ENTREGA", "ENTREGUE"):
            response = await self.client.patch(
                f"/orders/pedido/{pedido}/status",
                headers=self.autorizacao(3),
                json={"status": status},
            )
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["status"], status)
        self.assertEqual((await self.adicionar(pedido, produto)).status_code, 409)
        response = await self.client.post(
            f"/orders/pedido/cancelar/{pedido}",
            headers=self.autorizacao(),
        )
        self.assertEqual(response.status_code, 409)

    async def test_catalogo_permissoes_validacao_e_historico(self):
        dados = {"nome": "Pizza", "sabor": "Queijo", "tamanho": "M", "preco": "10.10"}
        for headers, esperado in (({}, 401), (self.autorizacao(), 403)):
            response = await self.client.post("/products/", headers=headers, json=dados)
            self.assertEqual(response.status_code, esperado)
        for alteracao in (
            {"preco": "0"},
            {"preco": "-1"},
            {"preco": "1.001"},
            {"nome": " "},
        ):
            response = await self.client.post(
                "/products/",
                headers=self.autorizacao(3),
                json={**dados, **alteracao},
            )
            self.assertEqual(response.status_code, 422, response.text)
        produto = await self.criar_produto("10.10")
        pedido = await self.criar_pedido()
        await self.adicionar(pedido, produto, 3)
        response = await self.client.put(
            f"/products/{produto}",
            headers=self.autorizacao(3),
            json={**dados, "preco": "99.99"},
        )
        self.assertEqual(response.status_code, 200)
        response = await self.client.delete(
            f"/products/{produto}", headers=self.autorizacao(3)
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual((await self.client.get("/products/")).json(), [])
        self.assertEqual(
            (await self.client.get(f"/products/{produto}")).status_code, 404
        )
        self.assertEqual((await self.adicionar(pedido, produto)).status_code, 404)
        response = await self.client.get(
            f"/orders/pedido/{pedido}", headers=self.autorizacao()
        )
        self.assertEqual(response.json()["preco"], "30.30")
        self.assertEqual(response.json()["itens"][0]["preco_unitario"], "10.10")
        response = await self.client.get("/products/admin", headers=self.autorizacao(3))
        self.assertFalse(response.json()[0]["ativo"])

    async def test_isolamento_dos_pedidos_e_itens(self):
        produto = await self.criar_produto()
        pedido = await self.criar_pedido()
        outro_pedido = await self.criar_pedido(2)
        response = await self.adicionar(pedido, produto)
        item = response.json()["itens"][0]["id"]
        self.assertEqual(
            (await self.adicionar(pedido, produto, usuario=2)).status_code, 403
        )
        for metodo, rota, corpo in (
            ("GET", f"/orders/pedido/{pedido}", None),
            ("DELETE", f"/orders/pedido/remover-item/{item}", None),
            ("PATCH", f"/orders/pedido/{pedido}/itens/{item}", {"quantidade": 1}),
            ("POST", f"/orders/pedido/cancelar/{pedido}", None),
            ("POST", f"/orders/pedido/finalizar/{pedido}", None),
        ):
            response = await self.client.request(
                metodo, rota, headers=self.autorizacao(2), json=corpo
            )
            self.assertEqual(response.status_code, 403, response.text)
        response = await self.client.patch(
            f"/orders/pedido/{outro_pedido}/itens/{item}",
            headers=self.autorizacao(2),
            json={"quantidade": 1},
        )
        self.assertEqual(response.status_code, 404)
        for usuario, esperado in (
            (1, [pedido]),
            (2, [outro_pedido]),
            (3, [outro_pedido, pedido]),
        ):
            response = await self.client.get(
                "/orders/listar", headers=self.autorizacao(usuario)
            )
            self.assertEqual([p["id"] for p in response.json()], esperado)
        response = await self.client.get(
            "/orders/listar/pedidos-usuario", headers=self.autorizacao(3)
        )
        self.assertEqual(response.json(), [])

    async def test_remover_item_recalcula_e_valida_quantidade(self):
        produto = await self.criar_produto()
        pedido = await self.criar_pedido()
        for quantidade in (0, -1, 101, 1.5, True):
            self.assertEqual(
                (await self.adicionar(pedido, produto, quantidade)).status_code, 422
            )
        response = await self.client.post(
            f"/orders/pedido/adicionar-item/{pedido}",
            headers=self.autorizacao(),
            json={"produto_id": produto, "quantidade": 1, "preco_unitario": "0.01"},
        )
        self.assertEqual(response.status_code, 422)
        response = await self.adicionar(pedido, produto)
        item = response.json()["itens"][0]["id"]
        response = await self.client.delete(
            f"/orders/pedido/remover-item/{item}", headers=self.autorizacao()
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["preco"], "0.00")
        self.assertEqual(response.json()["itens"], [])
        response = await self.client.post(
            f"/orders/pedido/finalizar/{pedido}", headers=self.autorizacao()
        )
        self.assertEqual(response.status_code, 409)
        with Session(self.engine) as session:
            self.assertIsNone(session.scalar(select(ItemPedido)))

    async def test_cancelamento_transicoes_e_paginacao(self):
        pedido = await self.criar_pedido()
        response = await self.client.patch(
            f"/orders/pedido/{pedido}/status",
            headers=self.autorizacao(),
            json={"status": "ENTREGUE"},
        )
        self.assertEqual(response.status_code, 403)
        response = await self.client.patch(
            f"/orders/pedido/{pedido}/status",
            headers=self.autorizacao(3),
            json={"status": "ENTREGUE"},
        )
        self.assertEqual(response.status_code, 409)
        response = await self.client.post(
            f"/orders/pedido/cancelar/{pedido}", headers=self.autorizacao()
        )
        self.assertEqual(response.json()["status"], "CANCELADO")
        response = await self.client.post(
            f"/orders/pedido/finalizar/{pedido}", headers=self.autorizacao()
        )
        self.assertEqual(response.status_code, 409)
        response = await self.client.get(
            "/orders/listar?status=CANCELADO&limit=1", headers=self.autorizacao()
        )
        self.assertEqual(len(response.json()), 1)
        for query in ("limit=101", "offset=-1", "status=INVALIDO"):
            response = await self.client.get(
                f"/orders/listar?{query}", headers=self.autorizacao()
            )
            self.assertEqual(response.status_code, 422)

    async def test_perfil_e_health(self):
        self.assertEqual((await self.client.get("/health")).json(), {"status": "ok"})
        self.assertEqual((await self.client.get("/auth/me")).status_code, 401)
        response = await self.client.get("/auth/me", headers=self.autorizacao())
        self.assertNotIn("senha", response.json())
        response = await self.client.patch(
            "/auth/me", headers=self.autorizacao(), json={"nome": " Novo "}
        )
        self.assertEqual(response.json()["nome"], "Novo")
        for dados in ({"nome": " "}, {"nome": "Novo", "admin": True}):
            response = await self.client.patch(
                "/auth/me", headers=self.autorizacao(), json=dados
            )
            self.assertEqual(response.status_code, 422)

    async def test_concorrencia_nao_sobrescreve_pedido(self):
        pedido_id = await self.criar_pedido()
        with Session(self.engine) as primeira, Session(self.engine) as segunda:
            pedido_a = primeira.get(Pedido, pedido_id)
            pedido_b = segunda.get(Pedido, pedido_id)
            pedido_a.status = "CANCELADO"
            primeira.commit()
            pedido_b.preco = Decimal("10.00")
            with self.assertRaises(StaleDataError):
                segunda.commit()
            segunda.rollback()
        with Session(self.engine) as session:
            pedido = session.get(Pedido, pedido_id)
            self.assertEqual(pedido.status, "CANCELADO")
            self.assertEqual(pedido.preco, Decimal("0.00"))
