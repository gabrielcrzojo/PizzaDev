"""Provisionamento explícito de administradores, sem cadastro público privilegiado.

Uso: python -m app.admin promover email@example.com
A conta deve ser cadastrada previamente pela API.
"""

import argparse

from sqlalchemy import func, select

from .dependencies import SessionLocal
from .models import Usuario


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("acao", choices=["promover"])
    parser.add_argument("email")
    args = parser.parse_args()
    with SessionLocal() as session:
        usuario = session.scalar(
            select(Usuario).where(
                func.lower(Usuario.email) == args.email.strip().lower()
            )
        )
        if usuario is None or not usuario.ativo:
            parser.error("Cadastre uma conta ativa antes de promovê-la.")
        usuario.admin = True
        session.commit()
    print("Conta promovida a administrador.")


if __name__ == "__main__":
    main()
