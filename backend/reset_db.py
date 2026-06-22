import sys
import os
from sqlalchemy import text

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from app.core.database import engine, Base
# Importar modelos para que Base los registre
from app.models import database_models

def main():
    print("⏳ Conectando y eliminando tablas en cascada...")
    with engine.connect() as conn:
        try:
            conn.execute(text("DROP TABLE IF EXISTS sentencias_chunks CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS sentencias_jueces CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS sentencias_vectors CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS sentencias CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS jueces CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS instancias CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS organos CASCADE;"))
            conn.commit()
            print("✅ Tablas eliminadas correctamente.")
        except Exception as e:
            conn.rollback()
            print(f"❌ Error al eliminar tablas: {e}")
            return

    print("⏳ Recreando tablas con el nuevo esquema...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Tablas recreadas correctamente.")
    except Exception as e:
        print(f"❌ Error al recrear tablas: {e}")

if __name__ == "__main__":
    main()
