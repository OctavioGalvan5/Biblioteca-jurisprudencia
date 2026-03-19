# 🚀 EMPEZAR AHORA - Paso a Paso

Sigue estos pasos **en orden** para tener la aplicación funcionando en 10 minutos.

---

## ✅ Paso 1: Iniciar PostgreSQL Local (1 minuto)

> **Nota:** El bucket de MinIO se creará automáticamente cuando inicies la app. ¡No necesitas hacerlo manualmente!

Abre una terminal (PowerShell o CMD) como Administrador:

```powershell
cd "C:\Users\octav\OneDrive\Escritorio\Estudio TYE\Biblioteca jurisprudencia"

# Iniciar solo PostgreSQL (sin MinIO)
docker-compose -f docker-compose-local.yml up -d
```

Espera ~30 segundos. Deberías ver:
```
Creating jurisprudencia_db ... done
Creating jurisprudencia_pgadmin ... done
```

Verifica que esté corriendo:
```powershell
docker ps
```

Deberías ver un contenedor con nombre `jurisprudencia_db`.

✅ **Listo!** PostgreSQL está corriendo en `localhost:5432`

---

## ✅ Paso 3: Configurar Backend (3 minutos)

En la misma terminal:

```powershell
cd backend

# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
venv\Scripts\activate

# Deberías ver (venv) al inicio de la línea

# Instalar dependencias (tarda ~2 minutos)
pip install -r requirements.txt
```

**Espera a que termine de instalar todas las librerías...**

Una vez que termine:

```powershell
# Cargar jueces de ejemplo
python seed_data.py
```

Deberías ver:
```
✓ Agregado: ANIBAL PINEDA
✓ Agregado: SILVINA ANDREA ANDALAF CASIFLLO
✓ Agregado: HERNAN DARIO MONTERCHIARINI
✓ Agregado: Fernando Lorenzo Barbara

✅ Proceso completado. 4 jueces agregados.
```

Ahora inicia el backend:

```powershell
python -m app.main
```

Deberías ver:
```
✅ Bucket 'sentencias' creado exitosamente en MinIO
   MinIO: 76.13.233.143:9000
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

O si el bucket ya existe:
```
✓ Bucket 'sentencias' ya existe en MinIO
INFO:     Started server process
...
```

✅ **Listo!** El backend está corriendo y el bucket está creado.

**NO CIERRES esta terminal.** Déjala abierta.

---

## ✅ Paso 4: Configurar Frontend (2 minutos)

Abre **OTRA terminal nueva** (PowerShell o CMD):

```powershell

cd "C:\Users\octav\OneDrive\Escritorio\Estudio TYE\Biblioteca jurisprudencia\frontend"

# Instalar dependencias (tarda ~1-2 minutos)
npm install
```

**Espera a que termine...**

Una vez que termine:

```powershell
npm run dev
```

Deberías ver:
```
▲ Next.js 14.x.x
- Local:        http://localhost:3000
- Ready in 2.3s
```

✅ **Listo!** El frontend está corriendo.

**NO CIERRES esta terminal.** Déjala abierta.

---

## ✅ Paso 5: Probar la Aplicación (2 minutos)

1. Abre tu navegador y ve a:
   ```
   http://localhost:3000
   ```

2. Deberías ver la página principal con:
   - Título: "Biblioteca de Jurisprudencia"
   - Zona de drag & drop para PDFs

3. **Arrastra** el archivo `sentencia.pdf` (que está en la raíz del proyecto)

4. Espera ~10-15 segundos. Verás:
   - Barra de progreso
   - Mensaje: "Procesando sentencia..."

5. Cuando termine, verás:
   - ✅ "Sentencia procesada exitosamente"
   - Datos extraídos:
     - Carátula
     - Nº Expediente
     - Órgano
     - Jueces detectados

6. Serás redirigido automáticamente a la página de edición

7. Revisa los datos, haz cambios si quieres, y click en **"Guardar Cambios"**

✅ **¡Funciona!** Has subido tu primera sentencia.

---

## 🎉 ¡LISTO!

Ahora tienes:

- ✅ PostgreSQL corriendo localmente
- ✅ MinIO en tu VPS funcionando
- ✅ Backend procesando PDFs con IA
- ✅ Frontend moderno
- ✅ Primera sentencia cargada

---

## 🔍 Verificar que Todo Funcionó

### Ver la API Docs

Abre en tu navegador:
```
http://localhost:8000/docs
```

Deberías ver la documentación Swagger de la API.

### Ver MinIO

1. Ve a: http://estudio-toyos-y-espin-minio-286854-76-13-233-143.traefik.me
2. Login (minioadmin / rifeoumd9teoom6m)
3. Click en bucket `sentencias`
4. Deberías ver el PDF que subiste

### Ver PostgreSQL

Abre pgAdmin (opcional):
```
http://localhost:5050
```
- Email: `admin@admin.com`
- Password: `admin`

---

## 🔄 Próximas Veces

Una vez que ya tienes todo instalado, para iniciar la app:

### Terminal 1 - Backend:
```powershell
cd "C:\Users\octav\OneDrive\Escritorio\Estudio TYE\Biblioteca jurisprudencia\backend"
venv\Scripts\activate
python -m app.main
```

### Terminal 2 - Frontend:
```powershell
cd "C:\Users\octav\OneDrive\Escritorio\Estudio TYE\Biblioteca jurisprudencia\frontend"
npm run dev
```

### O usa el script automático:
```powershell
.\start.bat
```

---

## 🐛 Si Algo Sale Mal

### "Database connection failed"

```powershell
# Verifica que Docker esté corriendo
docker ps

# Si no ves jurisprudencia_db, reinicia:
docker-compose -f docker-compose-local.yml up -d
```

### "MinIO connection failed"

1. Verifica que creaste el bucket `sentencias` en MinIO
2. Verifica que MinIO esté corriendo:
   ```powershell
   curl http://76.13.233.143:9000
   ```

### "OpenAI API error"

- Tu API key está en el `.env`
- Verifica que tengas créditos: https://platform.openai.com/usage

### "Module not found" (Python)

```powershell
cd backend
venv\Scripts\activate
pip install -r requirements.txt
```

### "Module not found" (Node)

```powershell
cd frontend
npm install
```

---

## 📚 Documentación Completa

- **[README.md](README.md)** - Documentación general
- **[TU_CONFIGURACION.md](TU_CONFIGURACION.md)** - Tu configuración específica
- **[GUIA_DOCKPLOY.md](GUIA_DOCKPLOY.md)** - Para deployar en VPS
- **[POSTGRESQL_DOCKPLOY.md](POSTGRESQL_DOCKPLOY.md)** - PostgreSQL en VPS

---

## 🎯 Siguiente Nivel: Deploy en VPS

Cuando quieras deployar en tu VPS con Dockploy, sigue:

**[GUIA_DOCKPLOY.md](GUIA_DOCKPLOY.md)**

---

## 💡 Tips

- Los datos extraídos por IA son **editables** - siempre revísalos
- Puedes agregar más jueces desde la API
- El sistema previene duplicados automáticamente
- Los PDFs se guardan en tu MinIO de VPS
- La base de datos está en tu PC (en desarrollo)

---

## ✅ Checklist

- [ ] Bucket `sentencias` creado en MinIO
- [ ] PostgreSQL corriendo (`docker ps`)
- [ ] Backend corriendo (puerto 8000)
- [ ] Frontend corriendo (puerto 3000)
- [ ] Jueces cargados (`seed_data.py`)
- [ ] Primera sentencia subida exitosamente
- [ ] Datos editados y guardados

Si todo está ✅, **¡estás listo para usar la aplicación!** 🎉
