from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Boolean, ForeignKey, ARRAY, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from ..core.database import Base


class Juez(Base):
    __tablename__ = "jueces"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=False)
    apellido = Column(String(255), nullable=False)
    activo = Column(Boolean, default=True)
    fecha_alta = Column(DateTime, default=func.now())
    fecha_baja = Column(DateTime, nullable=True)

    sentencias = relationship("SentenciaJuez", back_populates="juez")


class Sentencia(Base):
    __tablename__ = "sentencias"

    id = Column(Integer, primary_key=True, index=True)
    hash = Column(String(64), unique=True, nullable=False, index=True)
    caratula = Column(Text, nullable=True)
    nro_expediente = Column(String(100), nullable=True, index=True)
    fecha_sentencia = Column(Date, nullable=True, index=True)
    instancia = Column(String(100), nullable=True)
    organo = Column(String(200), nullable=True, index=True)
    jurisdiccion = Column(
        String(20),
        CheckConstraint("jurisdiccion IN ('federal', 'provincial')"),
        nullable=True,
        index=True,
    )
    palabras_clave = Column(ARRAY(Text), nullable=True)
    contenido = Column(Text, nullable=True)
    resumen = Column(Text, nullable=True)
    url_minio = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    jueces = relationship("SentenciaJuez", back_populates="sentencia", cascade="all, delete-orphan")


class SentenciaJuez(Base):
    __tablename__ = "sentencias_jueces"

    id = Column(Integer, primary_key=True, index=True)
    sentencia_id = Column(Integer, ForeignKey("sentencias.id", ondelete="CASCADE"), nullable=False)
    juez_id = Column(Integer, ForeignKey("jueces.id"), nullable=False)

    sentencia = relationship("Sentencia", back_populates="jueces")
    juez = relationship("Juez", back_populates="sentencias")


class SentenciaVector(Base):
    __tablename__ = "sentencias_vectors"

    id = Column(Integer, primary_key=True, index=True)
    sentencia_id = Column(Integer, ForeignKey("sentencias.id", ondelete="CASCADE"), nullable=False, unique=True)
    embedding = Column(Vector(1536), nullable=True)


class SentenciaChunk(Base):
    __tablename__ = "sentencias_chunks"

    id = Column(Integer, primary_key=True, index=True)
    sentencia_id = Column(Integer, ForeignKey("sentencias.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    tipo_seccion = Column(String(50), nullable=True)
    contenido = Column(Text, nullable=False)
    embedding = Column(Vector(1536), nullable=True)
