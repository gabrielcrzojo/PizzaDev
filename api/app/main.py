from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from .auth_routes import auth_router
from .catalog_routes import catalog_router
from .config import CORS_ORIGINS
from .dependencies import pegar_sessao
from .order_routes import order_router

app = FastAPI(
    title="PizzaDev API",
    version="1.0.0",
    description="Catálogo, contas e pedidos do PizzaDev. Sem processamento de pagamentos.",
)
if CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )


@app.exception_handler(StaleDataError)
async def conflito_concorrente(request, exc):
    return JSONResponse(
        status_code=409,
        content={
            "detail": "Pedido alterado por outra requisição. Consulte-o novamente antes de repetir a operação."
        },
    )


@app.get("/health", tags=["saúde"])
def health(session: Session = Depends(pegar_sessao)):
    session.execute(text("SELECT 1"))
    return {"status": "ok"}


# Cada módulo mantém suas rotas; a entrada apenas compõe a API.
app.include_router(auth_router)
app.include_router(order_router)
app.include_router(catalog_router)
