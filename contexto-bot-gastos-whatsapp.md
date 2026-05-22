# Bot de Control de Gastos por WhatsApp — Contexto del Proyecto

---

## Descripción

Bot de WhatsApp que permite a miembros de un equipo registrar gastos enviando fotos de recibos, PDFs, audios o texto. El bot extrae la información con IA, la clasifica y la registra automáticamente en Google Sheets y Google Drive.

Es un **servicio independiente** que cualquier equipo puede usar sin conocimientos técnicos. La integración con **ArquiCost** (Vercel + Supabase) viene en una fase posterior.

---

## Stack

| Componente | Tecnología |
|---|---|
| Backend | Python + FastAPI |
| IA | Gemini 1.5 Flash |
| WhatsApp | Meta Cloud API |
| Datos | Google Sheets (un Sheet por equipo) |
| Imágenes | Google Drive (una carpeta por equipo) |
| Hosting | Railway o Render |

---

## Cómo funciona para el usuario final

El administrador (quien despliega el bot) crea un grupo de WhatsApp y agrega a los miembros. Cada miembro simplemente envía fotos de recibos al grupo. El bot hace todo lo demás. Los miembros nunca interactúan con ninguna herramienta técnica.

Cada grupo de WhatsApp tiene:
- Su propio Google Sheet con los registros
- Su propia carpeta en Google Drive con las imágenes

---

## Estructura del Google Sheet

`Timestamp | Persona | Teléfono | Proveedor | Descripción | Categoría | Valor | Moneda | Fecha Recibo | Estado | Link Imagen`

Estados: `pendiente_revision` | `aprobado` | `rechazado`

---

## Categorías

| ID | Nombre | Ejemplos |
|---|---|---|
| materiales | Materiales | cemento, varilla, arena, pintura |
| herramientas | Herramientas | taladro, pala, andamio |
| viaticos | Viáticos | hotel, restaurante, tiquetes |
| transporte | Transporte | gasolina, flete, peaje |
| mano_obra | Mano de obra | jornal, operario, contratista |
| servicios | Servicios | electricidad, agua, internet |
| administrativo | Administrativo | papelería, notaría, permisos |
| otros | Otros | cualquier cosa que no encaje |

---

## Flujos de Usuario

**Flujo 1 — Foto/PDF con descripción en el mismo mensaje**
→ Procesar inmediatamente → Gemini → Registrar → Confirmar ✅

**Flujo 2 — Foto/PDF sin descripción, el usuario escribe después**
→ Iniciar timer 15 seg → llega texto del mismo usuario → combinar y procesar ✅

**Flujo 3 — Foto/PDF sin descripción, datos incompletos**
→ Esperar 15 seg → Gemini analiza solo → faltan datos → bot pregunta → registrar ✅

**Flujo 4 — Solo texto**
→ Procesar inmediatamente → si falta algo → preguntar → registrar ✅

**Flujo 5 — Audio**
→ Gemini transcribe y extrae → si falta algo → preguntar → registrar ✅

---

## Identificación de Remitentes (crítico)

```python
# Antes de cualquier procesamiento:
if message["from"] == os.getenv("BOT_PHONE_NUMBER"):
    return  # ignorar mensajes propios

if message["type"] in ["system", "notification"]:
    return  # ignorar mensajes del sistema
```

---

## Prompt a Gemini

Una sola llamada por registro. Responde únicamente JSON.

```
Eres un asistente que extrae datos de gastos.
Analiza el contenido y responde SOLO con JSON válido, sin texto adicional.

Categorías disponibles (usa el id exacto):
materiales, herramientas, viaticos, transporte, mano_obra, servicios, administrativo, otros

Extrae:
- valor: número sin símbolos
- moneda: "COP" por defecto
- proveedor: nombre del almacén o empresa
- descripcion: qué se compró
- fecha_recibo: YYYY-MM-DD (si no aparece, usa hoy)
- categoria_id: id exacto de la lista

Ejemplo:
{"valor":250000,"moneda":"COP","proveedor":"Ferretería El Perno",
"descripcion":"Bultos de cemento","fecha_recibo":"2025-05-21","categoria_id":"materiales"}

Si no puedes extraer un campo, ponlo null.
```

---

## Configuración de Grupos (administrador)

El administrador mantiene un archivo de configuración o Sheet auxiliar que mapea cada grupo de WhatsApp a su Sheet y carpeta de Drive:

```python
GRUPOS = {
  "chat_id_grupo_1": {
    "nombre": "Obra Laureles",
    "sheet_id": "...",
    "drive_folder_id": "..."
  },
  "chat_id_grupo_2": {
    "nombre": "Gastos Personales",
    "sheet_id": "...",
    "drive_folder_id": "..."
  }
}
```

---

## Variables de Entorno

```env
# WhatsApp
WHATSAPP_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_VERIFY_TOKEN=
BOT_PHONE_NUMBER=              # formato +57...

# IA
GEMINI_API_KEY=

# Google
GOOGLE_SERVICE_ACCOUNT_JSON=   # JSON de la service account como string
```

Los `sheet_id` y `drive_folder_id` van en la configuración de grupos, no en variables de entorno.

---

## Estrategia para reducir tokens y requests

- Una sola llamada a Gemini por registro (imagen + texto + instrucciones → JSON completo)
- No llamar a Gemini para mensajes del bot ni mensajes del sistema
- Deduplicar webhooks en memoria por `message_id` (WhatsApp a veces reenvía)

---

## Fases de Desarrollo

**Fase 1 — MVP**
- Webhook + filtro de remitente
- Flujo básico: foto + descripción → Gemini → Sheets + Drive
- Confirmación al usuario por WhatsApp

**Fase 2 — Flujos completos**
- Timer de 15 segundos
- Datos faltantes (bot pregunta)
- Soporte audio y PDF

**Fase 3 — Pulido**
- Manejo robusto de errores
- Logs en archivo o servicio externo (no en Sheets)
- Deduplicación robusta de webhooks

**Fase 4 — Integración con ArquiCost (futura)**
- Sincronización Sheets → Supabase
- Dashboard de gastos en ArquiCost
- Aprobación de gastos desde ArquiCost

---

## Notas

- El bot necesita servidor 24/7 — **no usar Vercel**. Usar Railway o Render.
- Un grupo de WhatsApp = un proyecto/equipo. El administrador crea el grupo y agrega miembros.
- Los miembros no necesitan saber nada técnico, solo usan WhatsApp normalmente.
- Gemini 1.5 Flash tiene capa gratuita generosa en Google AI Studio, ideal para pruebas.
- El número de WhatsApp Business debe ser dedicado al bot.
