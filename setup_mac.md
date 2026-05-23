# Guía de Configuración e Inicialización Automatizada para el Agente (macOS)

Este documento ha sido generado automáticamente para instruir al agente de IA en la MacBook Air sobre cómo configurar y ejecutar este proyecto de manera óptima en su nuevo entorno macOS.

> [!IMPORTANT]
> **Para el Agente de IA en macOS:**
> Lee este archivo por completo antes de ejecutar cualquier comando. Tu objetivo es configurar el entorno de desarrollo de Python local, restaurar dependencias y verificar el estado del servicio en el sistema operativo macOS.

---

## 1. Contexto del Proyecto
* **Nombre:** BOT CONARCA Gastos (Bot de control de gastos para CONARCA SAS).
* **Stack Principal:** Python 3.x, FastAPI, Uvicorn, Google Gemini API, Google Sheets API.
* **Sistema de Configuración:** Las variables de entorno críticas están gestionadas en el archivo `.env`.

---

## 2. Instrucciones de Configuración y Ejecución (Paso a Paso para el Agente)

### Paso 1: Limpieza del Entorno Previos (si aplica)
Si la carpeta fue copiada directamente desde Windows, podrían existir archivos binarios compilados o entornos virtuales inválidos.
* **Acción:** Elimina las carpetas `venv/`, `.venv/` o directorios de caché `__pycache__` si existen en el directorio raíz.
* **Comando recomendado:**
  ```bash
  rm -rf venv/ .venv/ **/__pycache__/
  ```

### Paso 2: Validación e Instalación de Python 3
* **Acción:** Verifica que la MacBook tenga Python 3 instalado.
* **Comando:**
  ```bash
  python3 --version
  ```
  *(Nota: Si no está instalado, notifica al usuario para instalarlo mediante Homebrew o la web oficial).*

### Paso 3: Creación y Activación del Entorno Virtual (macOS)
* **Acción:** Crea un entorno virtual limpio y actívalo.
* **Comandos:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### Paso 4: Instalación de Dependencias
* **Acción:** Instala las dependencias listadas en `requirements.txt`.
* **Comando:**
  ```bash
  pip install --upgrade pip
  pip install -r requirements.txt
  ```

### Paso 5: Verificación de Archivos Críticos
Asegúrate de que los siguientes archivos estén presentes en la raíz antes de intentar iniciar el servidor:
* `[x] .env` (Verifica que contenga las API Keys necesarias).
* `[x] gen-lang-client-0242224589-51dc274a3fb4.json` (Credenciales de Google Cloud/Sheets).
* `[x] grupos.json` (Archivo de configuración local).

### Paso 6: Ejecución del Servidor en Desarrollo Local
* **Acción:** Arranca el servidor FastAPI localmente utilizando `uvicorn`.
* **Comando:**
  ```bash
  uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
  ```

---

## 3. Estado de Verificación
Una vez realizadas las tareas anteriores, comprueba el funcionamiento del bot mediante una petición HTTP local al endpoint de salud:
* **Comando:**
  ```bash
  curl http://127.0.0.1:8000/
  ```
* **Resultado esperado:** Una respuesta JSON válida indicando que el servidor está arriba.
