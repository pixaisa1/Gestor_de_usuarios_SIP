# Gestor de Usuarios SIP - Asterisk

Este script en Python es una herramienta diseñada para facilitar la administración de extensiones en el archivo de configuración `sip.conf` de Asterisk. Permite realizar operaciones CRUD (Crear, Leer, Actualizar y Borrar) de forma segura y automatizada, ofreciendo tanto una interfaz interactiva como una interfaz de línea de comandos (CLI).

---

## Características Principales

- **Gestión Integral:** Añade, edita, elimina o lista usuarios SIP de forma sencilla.
- **Copias de Seguridad Automáticas:** Opción para crear un backup del archivo `sip.conf` antes de realizar cualquier modificación destructiva.
- **Modo Interactivo:** Una guía paso a paso ideal para administradores que prefieren no usar comandos complejos.
- **Interfaz CLI:** Soporte para argumentos de línea de comandos, perfecto para la automatización de tareas.
- **Parámetros Personalizables:** Configuración de parámetros SIP como `type`, `context`, `host`, `nat` y `canreinvite`.
- **Seguridad:** Manejo de contraseñas mediante entrada oculta en consola.

---

## Requisitos

- Python 3.x
- Permisos de superusuario (`sudo`) para modificar archivos en `/etc/asterisk/`.

---

## Instalación

1. Descarga el script `asterisk_add_user.py` en tu servidor Asterisk.
2. Asegúrate de tener permisos de ejecución:

```bash
chmod +x asterisk_add_user.py
```

---

## Uso

### 1. Modo Interactivo

Simplemente ejecuta el script sin argumentos para entrar en el menú asistido:

```bash
sudo python3 asterisk_add_user.py
```

### 2. Modo Línea de Comandos (CLI)

El script soporta varios comandos para operaciones rápidas:

**Añadir un usuario:**
```bash
sudo python3 asterisk_add_user.py add "usuario1" "password123" --context "ventas"
```

**Editar un usuario existente:**
```bash
sudo python3 asterisk_add_user.py edit "usuario1" "nueva_password" --nat "yes"
```

**Listar todos los usuarios:**
```bash
python3 asterisk_add_user.py list
```

**Eliminar un usuario:**
```bash
sudo python3 asterisk_add_user.py delete "usuario1"
```

---

## Configuración por Defecto

El script utiliza los siguientes valores por defecto para los nuevos usuarios, a menos que se especifique lo contrario:

| Parámetro | Valor por defecto |
|-----------|------------------|
| Archivo | `/etc/asterisk/sip.conf` |
| Contexto | `empleado` |
| Host | `dynamic` |
| NAT | `force_rport,comedia` |
| Canreinvite | `no` |

---

## Autor

**pixaisa1**

---

> ⚠️ **Nota:** Se recomienda encarecidamente realizar una copia de seguridad manual de sus archivos de configuración antes de utilizar herramientas de edición automatizada en entornos de producción.