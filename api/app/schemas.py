from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LoginSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    email: str = Field(
        min_length=3, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
    )
    senha: str = Field(min_length=1)

    @field_validator("email", mode="before")
    @classmethod
    def normalizar_email(cls, valor: object) -> object:
        # Cadastro e login usam o mesmo identificador, sem espaços ou caixa.
        return valor.strip().lower() if isinstance(valor, str) else valor

    @field_validator("senha")
    @classmethod
    def validar_tamanho_senha(cls, senha: str) -> str:
        # Bcrypt limita a entrada a 72 bytes, inclusive em senhas com acentos.
        if len(senha.encode("utf-8")) > 72:
            raise ValueError("A senha deve ter no máximo 72 bytes em UTF-8.")
        return senha


class UsuarioSchema(LoginSchema):
    nome: str = Field(min_length=1, max_length=120)
    # Cadastro público nunca concede privilégios administrativos.
    ativo: Literal[True] = True
    admin: Literal[False] = False

    @field_validator("nome")
    @classmethod
    def validar_nome(cls, nome: str) -> str:
        nome = nome.strip()
        if not nome:
            raise ValueError("Informe um nome válido.")
        return nome


# Preserva imports antigos sem perpetuar o erro de grafia no código novo.
UsarioSchema = UsuarioSchema


class PedidoSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    usuario: int = Field(gt=0)


class TokenSchema(BaseModel):
    access_token: str
    token_type: Literal["Bearer"] = "Bearer"


class LoginTokenSchema(TokenSchema):
    refresh_token: str


class UsuarioResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    email: str
    ativo: bool
    admin: bool


class PerfilSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    nome: str = Field(min_length=1, max_length=120)


class ProdutoSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    nome: str = Field(min_length=1, max_length=120)
    descricao: str = Field(default="", max_length=1000)
    sabor: str = Field(min_length=1, max_length=120)
    tamanho: str = Field(min_length=1, max_length=40)
    preco: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    ativo: bool = True


class ProdutoResposta(ProdutoSchema):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ItemPedidoSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    produto_id: int = Field(gt=0)
    quantidade: int = Field(gt=0, le=100, strict=True)


class QuantidadeSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    quantidade: int = Field(gt=0, le=100, strict=True)


class ItemResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    produto_id: int | None
    quantidade: int
    sabor: str
    tamanho: str
    preco_unitario: Decimal


StatusPedido = Literal[
    "PENDENTE", "FINALIZADO", "PREPARANDO", "EM_ENTREGA", "ENTREGUE", "CANCELADO"
]


class PedidoResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    usuario: int
    status: str
    preco: Decimal
    itens: list[ItemResposta]


class StatusSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: StatusPedido


class PedidoCriadoResposta(BaseModel):
    message: str
    id: int
