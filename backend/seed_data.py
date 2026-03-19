"""
Script para cargar datos iniciales en la base de datos
Ejecutar con: python seed_data.py
"""

from app.core.database import SessionLocal, engine
from app.models.database_models import Base, Juez

# Crear todas las tablas
Base.metadata.create_all(bind=engine)

# Jueces de ejemplo basados en la sentencia proporcionada
JUECES_INICIALES = [
    {"nombre": "ANIBAL", "apellido": "PINEDA"},
    {"nombre": "SILVINA ANDREA", "apellido": "ANDALAF CASIFLLO"},
    {"nombre": "HERNAN DARIO", "apellido": "MONTERCHIARINI"},
    {"nombre": "Fernando Lorenzo", "apellido": "Barbara"},
]


def seed_jueces():
    """Cargar jueces iniciales"""
    db = SessionLocal()

    try:
        # Verificar si ya existen jueces
        existing_count = db.query(Juez).count()

        if existing_count > 0:
            print(f"⚠️  Ya existen {existing_count} jueces en la base de datos.")
            respuesta = input("¿Deseas agregar los jueces de ejemplo de todos modos? (s/n): ")
            if respuesta.lower() != 's':
                print("Operación cancelada.")
                return

        # Agregar jueces
        jueces_agregados = 0
        for juez_data in JUECES_INICIALES:
            # Verificar si ya existe
            existe = db.query(Juez).filter(
                Juez.nombre == juez_data["nombre"],
                Juez.apellido == juez_data["apellido"]
            ).first()

            if not existe:
                juez = Juez(**juez_data, activo=True)
                db.add(juez)
                jueces_agregados += 1
                print(f"✓ Agregado: {juez_data['nombre']} {juez_data['apellido']}")
            else:
                print(f"○ Ya existe: {juez_data['nombre']} {juez_data['apellido']}")

        db.commit()
        print(f"\n✅ Proceso completado. {jueces_agregados} jueces agregados.")

        # Mostrar total
        total = db.query(Juez).count()
        print(f"📊 Total de jueces en la base de datos: {total}")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("CARGA DE DATOS INICIALES - Biblioteca de Jurisprudencia")
    print("=" * 60)
    print()

    seed_jueces()
