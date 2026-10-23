import os
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import httpx
from alembic.config import Config
from jose import jwt
from sqlalchemy import create_engine, event, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from alembic import command

# A suíte usa sua própria chave e um SQLite em memória, sem tocar no banco local.
with patch.dict(
    os.environ,
    {
        "SECRET_KEY": "chave-exclusiva-dos-testes-nao-usar-em-producao",
        "ALGORITHM": "HS256",
        "ACCESS_TOKEN_EXPIRE_MINUTES": "30",
    },
):
    from app import config
    from app.dependencies import pegar_sessao
    from app.main import app
    from app.models import Base, Pedido, Usuario, habilitar_chaves_estrangeiras
    from app.security import bcrypt_context, criar_token


class APITestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        event.listen(self.engine, "connect", habilitar_chaves_estrangeiras)
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            senha = bcrypt_context.hash("senha-teste")
            session.add_all(
                [
                    Usuario("Cliente", "cliente@example.com", senha),
                    Usuario("Outro", "outro@example.com", senha),
                    Usuario("Admin", "admin@example.com", senha, admin=True),
                ]
            )
            session.commit()

        def sessao_teste():
            with Session(self.engine) as session:
                yield session

        app.dependency_overrides[pegar_sessao] = sessao_teste
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://teste"
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        self.engine.dispose()

    def autorizacao(self, usuario=1, tipo="access", duracao=None):
        token = criar_token(usuario, duracao, tipo_token=tipo)
        return {"Authorization": f"Bearer {token}"}

    async def test_openapi_e_endpoints_publicos(self):
        response = await self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        fluxo = response.json()["components"]["securitySchemes"][
            "OAuth2PasswordBearer"
        ]["flows"]["password"]
        self.assertEqual(fluxo["tokenUrl"], "auth/login.form")
        for rota in ("/auth/", "/orders/", "/docs"):
            with self.subTest(rota=rota):
                self.assertEqual((await self.client.get(rota)).status_code, 200)

    async def test_cadastro_normaliza_email_e_armazena_hash(self):
        response = await self.client.post(
            "/auth/criar_conta",
            json={"nome": " Nova ", "email": " NOVA@EXAMPLE.COM ", "senha": "segredo"},
        )
        self.assertEqual(response.status_code, 200)
        with Session(self.engine) as session:
            usuario = session.scalar(
                select(Usuario).where(Usuario.email == "nova@example.com")
            )
            self.assertEqual(usuario.nome, "Nova")
            self.assertNotEqual(usuario.senha, "segredo")
            self.assertTrue(bcrypt_context.verify("segredo", usuario.senha))
            self.assertFalse(usuario.admin)
            self.assertTrue(usuario.ativo)

    async def test_cadastro_duplicado(self):
        response = await self.client.post(
            "/auth/criar_conta",
            json={
                "nome": "Cliente",
                "email": "CLIENTE@example.com",
                "senha": "segredo",
            },
        )
        self.assertEqual(response.status_code, 400)

    async def test_cadastro_nao_concede_privilegios(self):
        for campos in ({"admin": True}, {"ativo": False}):
            with self.subTest(campos=campos):
                response = await self.client.post(
                    "/auth/criar_conta",
                    json={
                        "nome": "Teste",
                        "email": "teste@example.com",
                        "senha": "segredo",
                        **campos,
                    },
                )
                self.assertEqual(response.status_code, 422)

    async def test_validacao_do_cadastro(self):
        for campos in (
            {"email": "invalido"},
            {"nome": "   "},
            {"senha": ""},
            {"senha": "á" * 37},
        ):
            with self.subTest(campos=campos):
                response = await self.client.post(
                    "/auth/criar_conta",
                    json={
                        "nome": "Teste",
                        "email": "teste@example.com",
                        "senha": "segredo",
                        **campos,
                    },
                )
                self.assertEqual(response.status_code, 422)

    async def test_login_json_emite_tokens_com_finalidades_diferentes(self):
        response = await self.client.post(
            "/auth/login",
            json={"email": " CLIENTE@EXAMPLE.COM ", "senha": "senha-teste"},
        )
        self.assertEqual(response.status_code, 200)
        dados = response.json()
        self.assertEqual(dados["token_type"], "Bearer")
        for campo, finalidade in (
            ("access_token", "access"),
            ("refresh_token", "refresh"),
        ):
            payload = jwt.decode(
                dados[campo], config.SECRET_KEY, algorithms=[config.ALGORITHM]
            )
            self.assertEqual(payload["sub"], "1")
            self.assertEqual(payload["type"], finalidade)

    async def test_login_formulario_do_swagger(self):
        response = await self.client.post(
            "/auth/login.form",
            data={"username": "cliente@example.com", "password": "senha-teste"},
        )
        self.assertEqual(response.status_code, 200)
        pedido = await self.client.post(
            "/orders/pedido",
            json={"usuario": 1},
            headers={"Authorization": f"Bearer {response.json()['access_token']}"},
        )
        self.assertEqual(pedido.status_code, 200)

    async def test_credenciais_invalidas_em_ambos_os_logins(self):
        for email in ("cliente@example.com", "ausente@example.com"):
            with self.subTest(email=email):
                responses = [
                    await self.client.post(
                        "/auth/login", json={"email": email, "senha": "errada"}
                    ),
                    await self.client.post(
                        "/auth/login.form",
                        data={"username": email, "password": "errada"},
                    ),
                ]
                for response in responses:
                    self.assertEqual(response.status_code, 401)
                    self.assertEqual(response.headers["WWW-Authenticate"], "Bearer")

    async def test_hash_legado_invalido_nao_causa_erro_500(self):
        with Session(self.engine) as session:
            session.get(Usuario, 1).senha = "hash-invalido"
            session.commit()
        response = await self.client.post(
            "/auth/login", json={"email": "cliente@example.com", "senha": "senha-teste"}
        )
        self.assertEqual(response.status_code, 401)

    async def test_refresh_exige_token_de_renovacao(self):
        for tipo, status in (("access", 401), ("refresh", 200)):
            with self.subTest(tipo=tipo):
                response = await self.client.post(
                    "/auth/refresh", headers=self.autorizacao(tipo=tipo)
                )
                self.assertEqual(response.status_code, status)

    async def test_pedido_exige_token_de_acesso(self):
        for headers, status in (
            ({}, 401),
            (self.autorizacao(tipo="refresh"), 401),
            (self.autorizacao(), 200),
        ):
            with self.subTest(status=status, headers=bool(headers)):
                response = await self.client.post(
                    "/orders/pedido", json={"usuario": 1}, headers=headers
                )
                self.assertEqual(response.status_code, status)
        with Session(self.engine) as session:
            pedido = session.scalar(select(Pedido))
            self.assertEqual(pedido.usuario, 1)
            self.assertEqual(pedido.preco, 0.0)
            self.assertEqual(pedido.status, "PENDENTE")

    async def test_pedido_respeita_proprietario_e_permissao_admin(self):
        response = await self.client.post(
            "/orders/pedido", json={"usuario": 2}, headers=self.autorizacao()
        )
        self.assertEqual(response.status_code, 403)
        response = await self.client.post(
            "/orders/pedido", json={"usuario": 2}, headers=self.autorizacao(usuario=3)
        )
        self.assertEqual(response.status_code, 200)
        response = await self.client.post(
            "/orders/pedido", json={"usuario": 999}, headers=self.autorizacao(usuario=3)
        )
        self.assertEqual(response.status_code, 404)

    async def test_usuario_inativo_nao_autentica_nem_renova(self):
        with Session(self.engine) as session:
            session.get(Usuario, 1).ativo = False
            session.commit()
        responses = [
            await self.client.post(
                "/auth/login",
                json={"email": "cliente@example.com", "senha": "senha-teste"},
            ),
            await self.client.post(
                "/auth/login.form",
                data={"username": "cliente@example.com", "password": "senha-teste"},
            ),
            await self.client.post(
                "/auth/refresh", headers=self.autorizacao(tipo="refresh")
            ),
            await self.client.post(
                "/orders/pedido", json={"usuario": 1}, headers=self.autorizacao()
            ),
        ]
        for response in responses:
            self.assertEqual(response.status_code, 403)

    async def test_tokens_invalidos_expirados_e_usuarios_inexistentes(self):
        tokens = [
            "invalido",
            criar_token(1, timedelta(minutes=-1)),
            criar_token(999),
            jwt.encode(
                {"sub": "abc", "exp": 9999999999, "type": "access"},
                config.SECRET_KEY,
                algorithm=config.ALGORITHM,
            ),
            jwt.encode(
                {"sub": "1", "type": "access"},
                config.SECRET_KEY,
                algorithm=config.ALGORITHM,
            ),
            jwt.encode(
                {"sub": "1", "exp": 9999999999},
                config.SECRET_KEY,
                algorithm=config.ALGORITHM,
            ),
            jwt.encode(
                {"sub": "1", "exp": 9999999999, "type": "access"},
                "outra-chave",
                algorithm=config.ALGORITHM,
            ),
        ]
        for token in tokens:
            with self.subTest(token=tokens.index(token)):
                response = await self.client.post(
                    "/orders/pedido",
                    json={"usuario": 1},
                    headers={"Authorization": f"Bearer {token}"},
                )
                self.assertEqual(response.status_code, 401)

    async def test_sqlite_rejeita_pedido_orfao(self):
        with Session(self.engine) as session:
            session.add(Pedido(usuario=999))
            with self.assertRaises(IntegrityError):
                session.commit()
            session.rollback()


class MigracoesTestCase(unittest.TestCase):
    def test_migracao_cria_schema_compativel_em_banco_temporario(self):
        with tempfile.TemporaryDirectory() as pasta:
            url = f"sqlite:///{Path(pasta) / 'teste.db'}"
            alembic_config = Config(str(config.API_DIR / "alembic.ini"))
            with patch.object(config, "DATABASE_URL", url):
                command.upgrade(alembic_config, "head")
                command.check(alembic_config)
            engine = create_engine(url)
            try:
                self.assertTrue(
                    {"usuarios", "pedidos", "itens_pedido"}.issubset(
                        inspect(engine).get_table_names()
                    )
                )
            finally:
                engine.dispose()

    def test_migracao_preserva_dados_legados_e_downgrade(self):
        from sqlalchemy import text

        with tempfile.TemporaryDirectory() as pasta:
            url = f"sqlite:///{Path(pasta) / 'legado.db'}"
            alembic_config = Config(str(config.API_DIR / "alembic.ini"))
            with patch.object(config, "DATABASE_URL", url):
                command.upgrade(alembic_config, "f2ddf0e0a5d5")
                engine = create_engine(url)
                try:
                    with engine.begin() as connection:
                        connection.execute(
                            text(
                                "INSERT INTO usuarios (id,nome,email,senha,ativo,admin) "
                                "VALUES (1,'Legado','legado@example.com','hash',1,0)"
                            )
                        )
                        connection.execute(
                            text(
                                "INSERT INTO pedidos (id,status,usuario,preco) VALUES (1,'PENDENTE',1,39.8)"
                            )
                        )
                        connection.execute(
                            text(
                                "INSERT INTO itens_pedido (id,quantidade,sabor,tamanho,preco_unitario,pedido) "
                                "VALUES (1,2,'Queijo','M',19.9,1)"
                            )
                        )
                    command.upgrade(alembic_config, "head")
                    command.check(alembic_config)
                    with Session(engine) as session:
                        pedido = session.get(Pedido, 1)
                        self.assertEqual(str(pedido.preco), "39.80")
                        self.assertEqual(pedido.versao, 1)
                        self.assertEqual(len(pedido.itens), 1)
                        self.assertIsNone(pedido.itens[0].produto_id)
                        self.assertEqual(str(pedido.itens[0].preco_unitario), "19.90")
                    command.downgrade(alembic_config, "f2ddf0e0a5d5")
                    with engine.connect() as connection:
                        self.assertEqual(
                            connection.scalar(text("SELECT COUNT(*) FROM pedidos")), 1
                        )
                        self.assertEqual(
                            connection.scalar(
                                text("SELECT COUNT(*) FROM itens_pedido")
                            ),
                            1,
                        )
                    command.upgrade(alembic_config, "head")
                    command.check(alembic_config)
                finally:
                    engine.dispose()
