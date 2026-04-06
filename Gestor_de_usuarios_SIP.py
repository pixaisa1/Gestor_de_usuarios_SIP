#!/usr/bin/env python3
"""
asterisk_add_user.py
Agrega usuarios SIP al archivo sip.conf de Asterisk de forma sencilla y automatica.
Ejecuta sin argumentos para modo interactivo guiado.
"""

import os
import sys
import argparse
import re
import getpass
from datetime import datetime

SIP_CONF_PATH = "/etc/asterisk/sip.conf"
BACKUP_SUFFIX = ".bak"

DEFAULT_USER_PARAMS = {
    "type": "friend",
    "context": "empleado",
    "host": "dynamic",
    "canreinvite": "no",
    "nat": "force_rport,comedia",
}

# ─────────────────────────────────────────────
# Helpers de entrada interactiva
# ─────────────────────────────────────────────

def preguntar(mensaje: str, por_defecto: str = "") -> str:
    """Pide un valor al usuario con un valor por defecto opcional."""
    if por_defecto:
        prompt = f"  {mensaje} [{por_defecto}]: "
    else:
        prompt = f"  {mensaje}: "
    while True:
        respuesta = input(prompt).strip()
        if respuesta:
            return respuesta
        if por_defecto:
            return por_defecto
        print("  [!] Este campo es obligatorio.")


def preguntar_password(mensaje: str = "Contraseña SIP") -> str:
    """Pide una contraseña ocultando la entrada."""
    while True:
        pwd = getpass.getpass(f"  {mensaje}: ")
        if pwd:
            return pwd
        print("  [!] La contraseña no puede estar vacía.")


def preguntar_si_no(mensaje: str, por_defecto: bool = True) -> bool:
    """Pregunta si/no."""
    opciones = "S/n" if por_defecto else "s/N"
    respuesta = input(f"  {mensaje} [{opciones}]: ").strip().lower()
    if not respuesta:
        return por_defecto
    return respuesta in ("s", "si", "sí", "y", "yes")


def separador(titulo: str = "") -> None:
    linea = "─" * 50
    if titulo:
        print(f"\n{linea}")
        print(f"  {titulo}")
        print(f"{linea}")
    else:
        print(linea)


def backup_conf(path: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{path}{BACKUP_SUFFIX}.{timestamp}"
    try:
        with open(path, "r") as original:
            content = original.read()
        with open(backup_path, "w") as backup:
            backup.write(content)
        print(f"  [✓] Backup creado: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"  [!] No se pudo crear backup: {e}")
        sys.exit(1)


def user_exists(path: str, username: str) -> bool:
    pattern = re.compile(rf"^\[{re.escape(username)}\]", re.MULTILINE)
    try:
        with open(path, "r") as f:
            content = f.read()
        return bool(pattern.search(content))
    except FileNotFoundError:
        return False


def build_user_block(username: str, secret: str, **kwargs) -> str:
    params = {**DEFAULT_USER_PARAMS, **kwargs}
    lines = [f"[{username}]"]
    lines.append(f"secret={secret}")
    for key, value in params.items():
        lines.append(f"{key}={value}")
    lines.append("")
    return "\n".join(lines)


def add_user(path: str, username: str, secret: str, **kwargs) -> bool:
    if user_exists(path, username):
        print(f"  [!] El usuario '{username}' ya existe en {path}. Omitiendo.")
        return False

    user_block = build_user_block(username, secret, **kwargs)

    try:
        with open(path, "a") as f:
            f.write(f"\n{user_block}\n")
        print(f"  [✓] Usuario '{username}' agregado correctamente.")
        return True
    except PermissionError:
        print(f"  [✗] Sin permisos para escribir en {path}. Ejecuta con sudo.")
        sys.exit(1)
    except Exception as e:
        print(f"  [✗] Error al escribir en {path}: {e}")
        sys.exit(1)


def ensure_general_section(path: str) -> None:
    if not os.path.exists(path):
        print(f"  [i] {path} no encontrado. Creando nuevo archivo...")
        general_block = (
            "[general]\n"
            "port=5060\n"
            "directmedia=no\n"
            "language=es\n"
            "context=public\n"
        )
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(general_block)
            print(f"  [✓] Archivo {path} creado con sección [general].")
        except PermissionError:
            print(f"  [✗] Sin permisos para crear {path}. Ejecuta con sudo.")
            sys.exit(1)


def list_users(path: str) -> None:
    pattern = re.compile(r"^\[([^\]]+)\]", re.MULTILINE)
    try:
        with open(path, "r") as f:
            content = f.read()
        sections = pattern.findall(content)
        users = [s for s in sections if s.lower() != "general"]
        if users:
            print(f"\n  Usuarios SIP en {path}:")
            for u in users:
                print(f"    - {u}")
        else:
            print("  No hay usuarios SIP configurados.")
    except FileNotFoundError:
        print(f"  [!] Archivo {path} no encontrado.")


def delete_user(path: str, username: str) -> bool:
    if not user_exists(path, username):
        print(f"  [!] El usuario '{username}' no existe en {path}.")
        return False

    try:
        with open(path, "r") as f:
            content = f.read()

        pattern = re.compile(
            rf"\n?\[{re.escape(username)}\][^\[]*",
            re.DOTALL
        )
        new_content = pattern.sub("", content).strip() + "\n"

        with open(path, "w") as f:
            f.write(new_content)

        print(f"  [✓] Usuario '{username}' eliminado correctamente.")
        return True
    except PermissionError:
        print(f"  [✗] Sin permisos para modificar {path}. Ejecuta con sudo.")
        sys.exit(1)


# ─────────────────────────────────────────────
# Modo interactivo
# ─────────────────────────────────────────────

def modo_interactivo() -> None:
    print("\n╔══════════════════════════════════════════════╗")
    print("║      Gestor de usuarios SIP - Asterisk       ║")
    print("╚══════════════════════════════════════════════╝")

    # 1. Ruta del archivo
    separador("Configuración del archivo")
    conf_path = preguntar("Ruta al sip.conf", SIP_CONF_PATH)

    # 2. Menú de acción
    separador("¿Qué quieres hacer?")
    print("  1) Agregar usuario")
    print("  2) Eliminar usuario")
    print("  3) Listar usuarios")
    print("  4) Salir")

    while True:
        opcion = input("\n  Elige una opción [1-4]: ").strip()
        if opcion in ("1", "2", "3", "4"):
            break
        print("  [!] Opción no válida, elige entre 1 y 4.")

    if opcion == "4":
        print("\n  Hasta luego.\n")
        sys.exit(0)

    if opcion == "3":
        separador("Usuarios existentes")
        list_users(conf_path)
        print()
        return

    if opcion == "2":
        separador("Eliminar usuario")
        list_users(conf_path)
        username = preguntar("Nombre del usuario a eliminar")
        hacer_backup = preguntar_si_no("¿Crear backup antes de eliminar?")
        if hacer_backup and os.path.exists(conf_path):
            backup_conf(conf_path)
        delete_user(conf_path, username)
        print()
        return

    # opcion == "1" → Agregar usuario
    separador("Datos del nuevo usuario")

    username = preguntar("Nombre de usuario")
    secret   = preguntar_password("Contraseña SIP")

    separador("Parámetros avanzados (Enter para usar el valor por defecto)")
    tipo     = preguntar("type",        DEFAULT_USER_PARAMS["type"])
    context  = preguntar("context",     DEFAULT_USER_PARAMS["context"])
    host     = preguntar("host",        DEFAULT_USER_PARAMS["host"])
    nat      = preguntar("nat",         DEFAULT_USER_PARAMS["nat"])
    canreinv = preguntar("canreinvite", DEFAULT_USER_PARAMS["canreinvite"])

    # Resumen antes de confirmar
    separador("Resumen")
    print(f"  Archivo     : {conf_path}")
    print(f"  Usuario     : {username}")
    print(f"  type        : {tipo}")
    print(f"  context     : {context}")
    print(f"  host        : {host}")
    print(f"  nat         : {nat}")
    print(f"  canreinvite : {canreinv}")

    if not preguntar_si_no("\n¿Confirmar y guardar?"):
        print("\n  Operación cancelada.\n")
        return

    hacer_backup = preguntar_si_no("¿Crear backup antes de guardar?")

    separador("Guardando")
    ensure_general_section(conf_path)
    if hacer_backup and os.path.exists(conf_path):
        backup_conf(conf_path)

    add_user(conf_path, username, secret,
             type=tipo, context=context, host=host,
             nat=nat, canreinvite=canreinv)
    print()


# ─────────────────────────────────────────────
# Modo CLI (con argumentos)
# ─────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Gestiona usuarios SIP en sip.conf de Asterisk. "
                    "Sin argumentos lanza el modo interactivo."
    )
    subparsers = parser.add_subparsers(dest="command")

    add_p = subparsers.add_parser("add", help="Agregar un usuario SIP")
    add_p.add_argument("username")
    add_p.add_argument("secret")
    add_p.add_argument("--context",     default=DEFAULT_USER_PARAMS["context"])
    add_p.add_argument("--type",        default=DEFAULT_USER_PARAMS["type"])
    add_p.add_argument("--host",        default=DEFAULT_USER_PARAMS["host"])
    add_p.add_argument("--nat",         default=DEFAULT_USER_PARAMS["nat"])
    add_p.add_argument("--canreinvite", default=DEFAULT_USER_PARAMS["canreinvite"])
    add_p.add_argument("--conf",        default=SIP_CONF_PATH)
    add_p.add_argument("--no-backup",   action="store_true")

    list_p = subparsers.add_parser("list", help="Listar usuarios SIP")
    list_p.add_argument("--conf", default=SIP_CONF_PATH)

    del_p = subparsers.add_parser("delete", help="Eliminar un usuario SIP")
    del_p.add_argument("username")
    del_p.add_argument("--conf",      default=SIP_CONF_PATH)
    del_p.add_argument("--no-backup", action="store_true")

    return parser.parse_args()


def main():
    # Sin argumentos → modo interactivo completo
    if len(sys.argv) == 1:
        modo_interactivo()
        return

    args = parse_args()

    if args.command == "add":
        ensure_general_section(args.conf)
        if not args.no_backup and os.path.exists(args.conf):
            backup_conf(args.conf)
        add_user(args.conf, args.username, args.secret,
                 type=args.type, context=args.context,
                 host=args.host, canreinvite=args.canreinvite, nat=args.nat)

    elif args.command == "list":
        list_users(args.conf)

    elif args.command == "delete":
        if not args.no_backup and os.path.exists(args.conf):
            backup_conf(args.conf)
        delete_user(args.conf, args.username)


if __name__ == "__main__":
    main()