from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from .core.config import settings
from .core.database import engine, Base
from .api.routes import upload, sentencias, jueces, auth, chat, instancias, organos

print("⏳ Conectando a PostgreSQL y creando tablas...")
try:
    # Habilitar extensión pgvector antes de crear tablas
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    Base.metadata.create_all(bind=engine)

    # Agregar columna embedding si la tabla ya existía sin ella
    with engine.connect() as conn:
        conn.execute(text("""
            ALTER TABLE sentencias_vectors
            ADD COLUMN IF NOT EXISTS embedding vector(1536)
        """))
        conn.execute(text("""
            ALTER TABLE sentencias_chunks
            ADD COLUMN IF NOT EXISTS embedding vector(1536)
        """))
        conn.commit()

    print("✅ Base de datos lista")
except Exception as e:
    print(f"❌ Error al conectar con PostgreSQL: {e}")
    print(f"   URL: {settings.DATABASE_URL}")

# Crear aplicación FastAPI
app = FastAPI(
    title="Biblioteca Jurisprudencia API",
    description="API para gestión de sentencias judiciales con IA",
    version="1.0.0",
    debug=settings.DEBUG
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:3000",
        "https://biblioteca.estudiotye.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(auth.router, prefix="/api")
app.include_router(upload.router, prefix="/api")
app.include_router(sentencias.router, prefix="/api")
app.include_router(jueces.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(instancias.router, prefix="/api")
app.include_router(organos.router, prefix="/api")


@app.get("/")
def root():
    return {
        "message": "Biblioteca Jurisprudencia API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG
    )
