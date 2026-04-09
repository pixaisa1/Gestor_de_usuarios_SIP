# Gestor Integral de Asterisk v2.2

Una herramienta potente y versátil escrita en Python para la administración de usuarios (PJSIP/SIP) y extensiones (Dialplan) en servidores Asterisk. Permite gestionar configuraciones mediante una interfaz interactiva en consola o a través de comandos directos (CLI).

---

## Características Principales

- **Soporte Dual:** Maneja tanto el stack moderno `chan_pjsip` como el antiguo `chan_sip`.
- **Gestión de Dialplan:** Crea, edita y elimina extensiones en `extensions.conf` de forma automática.
- **Seguridad:** Sistema de backups automáticos antes de cualquier modificación crítica.
- **Recarga Automática:** Ejecuta comandos de `asterisk -rx 'reload'` de forma inteligente tras cada cambio.
- **Modo Híbrido:** Úsalo mediante menús intuitivos o automatiza tareas con argumentos de línea de comandos.

---

## Requisitos

1. Asterisk instalado y configurado en el sistema.
2. Python 3.x.
3. Permisos de Sudo (necesarios para editar archivos en `/etc/asterisk/` y ejecutar comandos de recarga).

---

## Instalación y Uso

Dale permisos de ejecución al script:

```bash
chmod +x asterisk_manager.py
```

### 1. Modo Interactivo (Menús)

Simplemente ejecuta el script sin parámetros para entrar en la interfaz visual:

```bash
sudo ./asterisk_manager.py
```

### 2. Modo CLI (Comandos Directos)

Ideal para automatizaciones o usuarios avanzados:

- **Añadir Usuario:**
  ```bash
  sudo ./asterisk_manager.py add-user 101 Secreto123 --protocol pjsip
  ```

- **Asignar Extensión:**
  ```bash
  sudo ./asterisk_manager.py add-exten 101 usuario101 --context from-internal
  ```

- **Listar Usuarios:**
  ```bash
  sudo ./asterisk_manager.py list-users --protocol pjsip
  ```

- **Eliminar Extensión:**
  ```bash
  sudo ./asterisk_manager.py del-exten 101
  ```

---

## Archivos Gestionados

El script actúa sobre las rutas estándar de Asterisk, aunque estas pueden ser modificadas durante la ejecución interactiva:

- `/etc/asterisk/pjsip.conf`
- `/etc/asterisk/sip.conf`
- `/etc/asterisk/extensions.conf`

> [!IMPORTANT]
> Los backups se guardan con el sufijo `.bak.YYYYMMDD_HHMMSS` en el mismo directorio que el archivo original.

---

## Estructura Técnica

| Función | Descripción |
|---|---|
| `backup_conf` | Crea copias de seguridad con timestamp. |
| `reload_asterisk` | Detecta el cambio y aplica `sip/pjsip/dialplan reload`. |
| `ensure_file_structure` | Crea los archivos de configuración con cabeceras básicas si no existen. |
| `build_user_blocks` | Genera los bloques de texto según el estándar del protocolo elegido. |

---

## ❤️ Contribución
Hecho por **pixaisa1** y **Vlad0n4ik**. Siéntete libre de clonar, mejorar o reportar bugs.

> **Nota:** Este script está diseñado para entornos de administración. Se recomienda probar en entornos de desarrollo antes de aplicar cambios masivos en servidores de producción.
