import sqlalchemy
engine = sqlalchemy.create_engine("postgresql://postgres:mglzazv4lrzxfmzi@76.13.233.143:5433/postgres")
with engine.connect() as conn:
    r1 = conn.execute(sqlalchemy.text("DELETE FROM sentencias_jueces"))
    r2 = conn.execute(sqlalchemy.text("DELETE FROM jueces"))
    conn.commit()
    print(f"Eliminados {r1.rowcount} relaciones sentencia-juez")
    print(f"Eliminados {r2.rowcount} jueces")
    print("Listo!")
