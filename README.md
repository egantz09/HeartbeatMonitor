# HeartbeatMonitor

**Monitor de disponibilidad y uptime para Windows.**

Aplicación de escritorio (Python + PyQt6) que registra el tiempo de encendido/apagado del equipo,
detecta cortes eléctricos, caídas de red, suspensiones y genera reportes de disponibilidad
en Excel y PDF.

> Creada por **Soluciones Melis** — solucionesmelis@gmail.com

---

## ✨ Características

### Monitorización del sistema
- **Heartbeat** cada 60 s (configurable) → guarda el estado en `state.json`
- **Detección de cortes eléctricos** por dos fuentes independientes:
  - Delta de heartbeat (si el equipo estuvo apagado > 150 s)
  - Windows Event Log ID 41 (Kernel-Power) → fuente fiable a prueba de fallos
- **Suspensión / reanudación** vía `WM_POWERBROADCAST`
- **Cierre limpio** vs apagado brusco
- **Autoarranque** al iniciar sesión de Windows

### Monitorización de red (opcional, desactivable)
- **Multi-ping** a varios hosts simultáneamente (`8.8.8.8`, `1.1.1.1`, `tudominio.com`…)
- Detección de **caídas y recuperaciones** por host
- Tarjetas + gráficas independientes por host
- Eventos `NET_DOWN` / `NET_UP` con notificación de bandeja

### Interfaz gráfica (5 pestañas)
| Pestaña | Contenido |
|---|---|
| **Dashboard** | KPIs de uptime (30 d / 7 d / hoy), MTBF, MTTR, SLA, estado de red |
| **Eventos** | Tabla filtrable + rango de fechas + duración de cada evento + export PDF |
| **Analítica** | Cortes por hora, cortes por día de la semana, top 5 más largos |
| **Métricas** | Tarjeta + gráfica de ping por host (rango "Hoy" por defecto) |
| **Configuración** | Tema, notificaciones, hosts, umbrales, toggles |

### Extras
- 🌗 **Modo oscuro / claro**
- 🎨 **Splash screen** con marca
- 📥 **Bandeja del sistema** con menú contextual
- 🔔 **Notificaciones** de bandeja ante eventos críticos
- 📊 **Export a Excel** (con hoja de portada)
- 📄 **Export a PDF** (mes completo o rango personalizado)
- 🖼️ **Icono personalizado** en barra de tareas, título y bandeja

---

## 📸 Capturas

> _(Añade aquí capturas de las pestañas Dashboard, Eventos, Analítica, Métricas y Configuración)_
