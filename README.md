# Gestor Integral de Asterisk v3.0

Una herramienta potente y versátil escrita en Python para la administración de usuarios (PJSIP/SIP) y extensiones (Dialplan) en servidores Asterisk. Permite gestionar configuraciones tanto desde **archivos locales** como desde una **base de datos MySQL/MariaDB**, mediante una interfaz interactiva en consola o a través de comandos directos (CLI).

---

## Características Principales

- **Soporte Dual de Protocolo:** Maneja tanto el stack moderno `chan_pjsip` como el antiguo `chan_sip`.
- **Soporte Dual de Almacenamiento:** Gestiona usuarios desde archivos locales (`pjsip.conf` / `sip.conf`) o directamente desde una base de datos MySQL/MariaDB.
- **Gestión de Dialplan:** Crea, edita y elimina extensiones en `extensions.conf` de forma automática.
- **Parámetros NAT/RTP automáticos:** Todos los usuarios creados incluyen `direct_media=no`, `force_rport=yes` y `rewrite_contact=yes` para garantizar el correcto funcionamiento del audio en entornos con NAT.
- **Caché de conexión:** Los datos de conexión a la base de datos se guardan localmente (sin contraseña) para no tener que introducirlos en cada sesión.
- **Seguridad:** Sistema de backups automáticos antes de cualquier modificación crítica.
- **Recarga Automática:** Ejecuta comandos `asterisk -rx 'reload'` de forma inteligente tras cada cambio.
- **Modo Híbrido:** Úsalo mediante menús intuitivos o automatiza tareas con argumentos de línea de comandos.

---

## Requisitos

1. Asterisk instalado y configurado en el sistema.
2. Python 3.x.
3. Permisos de `sudo` (necesarios para editar archivos en `/etc/asterisk/` y ejecutar comandos de recarga).
4. *(Solo modo base de datos)* Módulo `mysql-connector-python`:
   ```bash
   pip install mysql-connector-python --break-system-packages
   ```

---

## Instalación

Descarga el script en tu servidor Asterisk:

```bash
wget https://raw.githubusercontent.com/pixaisa1/Gestor_de_usuarios_SIP/Feature/BaseDatos/Gestor_de_usuarios_SIP.py
```

Dale permisos de ejecución:

```bash
chmod +x Gestor_de_usuarios_SIP.py
```

---

## Uso

### 1. Modo Interactivo (Menús)

Ejecuta el script sin parámetros para entrar en la interfaz visual:

```bash
sudo python3 Gestor_de_usuarios_SIP.py
```

Al arrancar, el programa preguntará dónde están almacenados los usuarios:

```
  ¿Dónde están almacenados los usuarios?
  1) Archivos locales  (sip.conf / pjsip.conf)
  2) Base de datos     (MySQL / MariaDB)
```

**Modo archivos locales** — gestiona directamente `pjsip.conf` o `sip.conf`.

**Modo base de datos** — solicita los datos de conexión (host, puerto, nombre de BD, usuario y contraseña). A partir de la segunda vez, ofrece reutilizar los datos guardados en caché (`~/.asterisk_manager_cache.json`) para conectar más rápido.

### 2. Modo CLI (Comandos Directos)

Ideal para automatizaciones o usuarios avanzados:

**Añadir usuario:**
```bash
sudo python3 Gestor_de_usuarios_SIP.py add-user 101 Secreto123 --protocol pjsip
```

**Editar usuario:**
```bash
sudo python3 Gestor_de_usuarios_SIP.py edit-user 101 --password NuevaClave --protocol pjsip
```

**Eliminar usuario:**
```bash
sudo python3 Gestor_de_usuarios_SIP.py del-user 101 --protocol pjsip
```

**Listar usuarios:**
```bash
sudo python3 Gestor_de_usuarios_SIP.py list-users --protocol pjsip
```

**Asignar extensión:**
```bash
sudo python3 Gestor_de_usuarios_SIP.py add-exten 101 usuario101 --context from-internal
```

**Eliminar extensión:**
```bash
sudo python3 Gestor_de_usuarios_SIP.py del-exten 101
```

**Listar extensiones:**
```bash
sudo python3 Gestor_de_usuarios_SIP.py list-extens
```

> Añade `--no-backup` para omitir el backup y `--no-reload` para no recargar Asterisk automáticamente.

---

## Archivos Gestionados

El script actúa sobre las rutas estándar de Asterisk, aunque pueden modificarse durante la ejecución interactiva:

- `/etc/asterisk/pjsip.conf`
- `/etc/asterisk/sip.conf`
- `/etc/asterisk/extensions.conf`

> [!IMPORTANT]
> Los backups se guardan con el sufijo `.bak.YYYYMMDD_HHMMSS` en el mismo directorio que el archivo original.

---

## Estructura de Base de Datos

El modo base de datos opera sobre las tres tablas estándar de Asterisk PJSIP:

| Tabla | Contenido |
|---|---|
| `ps_endpoints` | Endpoint del usuario (contexto, codecs, NAT) |
| `ps_auths` | Credenciales (usuario y contraseña) |
| `ps_aors` | Registro de dirección (max_contacts) |

Los campos NAT/RTP se insertan automáticamente en `ps_endpoints`:

| Campo | Valor |
|---|---|
| `direct_media` | `no` |
| `force_rport` | `yes` |
| `rewrite_contact` | `yes` |

---

## Estructura Técnica

| Función | Descripción |
|---|---|
| `backup_conf` | Crea copias de seguridad con timestamp. |
| `reload_asterisk` | Detecta el cambio y aplica `sip/pjsip/dialplan reload`. |
| `ensure_file_structure` | Crea los archivos de configuración con cabeceras básicas si no existen. |
| `build_user_blocks` | Genera los bloques de texto según el estándar del protocolo elegido, incluyendo parámetros NAT/RTP. |
| `login_db` | Gestiona la conexión a la BD con soporte de caché. |
| `db_add_user` | Inserta los tres registros necesarios en la BD (`endpoint`, `auth`, `aor`). |
| `db_edit_user` | Actualiza las credenciales y parámetros de un usuario existente en la BD. |
| `cargar_cache_db` / `guardar_cache_db` | Guarda y recupera los datos de conexión (sin contraseña) en `~/.asterisk_manager_cache.json`. |

---

## ❤️ Contribución

Hecho por **pixaisa1** y **Vlad0n4ik**. Siéntete libre de clonar, mejorar o reportar bugs.

> **Nota:** Este script está diseñado para entornos de administración. Se recomienda probar en entornos de desarrollo antes de aplicar cambios masivos en servidores de producción.
