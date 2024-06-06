# pas pour insérer les données, mais pourquoi pas pour l'analyse
#
#
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy import insert
from sqlalchemy import ForeignKey
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)
from sqlalchemy.types import SmallInteger
import os

dbname = "litteralement"
username = os.getenv("USER")
engine = create_engine(f"postgresql+psycopg://{username}@/{dbname}")


class Base(DeclarativeBase):
    pass


class Classe(Base):
    __tablename__ = "classe"
    id: Mapped[int] = mapped_column(
        primary_key=True,
        type_=SmallInteger,
        nullable=False,
    )
    nom: Mapped[str] = mapped_column(
        unique=True,
        nullable=False,
    )


class Entity(Base):
    __tablename__ = "entite"
    id: Mapped[int] = mapped_column(primary_key=True)
    classe: Mapped[int] = mapped_column(ForeignKey("classe.id"))

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, name={self.name!r}, fullname={self.fullname!r})"

    # @property
    # def classe_name(self):
    #     # ok si ça ça fonctionne ce serait incroyable..?
    #     # ou mieux: entite1.classe.name
    #     pass


# Base.metadata.create_all()

chose1 = insert(Entity)


# Entity(id=1, classe=0)

chose1.classe

with engine.connect() as conn:
    result = conn.execute(insert(Classe).values(id=1, nom="lieu"))

with engine.connect() as conn:
    result = conn.execute(insert(Entity).values(classe=1))
    lieu1 = insert(Entity).values(classe=1).returning(Entity.id)
    conn.commit()

lieu1 = insert(Entity).values(
    classe=1
)  # mais ça, c'est pas l'objet, hélas
