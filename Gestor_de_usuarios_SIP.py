#!/usr/bin/env python3

import os
import sys
import argparse
import re
import getpass
import subprocess
from datetime import datetime

# CONFIGURACIÓN Y CONSTANTES
SIP_CONF_PATH = "/etc/asterisk/sip.conf"
PJSIP_CONF_PATH = "/etc/asterisk/pjsip.conf"
BACKUP_SUFFIX = ".bak"

DEFAULT_PARAMS = {
    "sip": {
        "type": "friend",
        "context": "empleado",
        "host": "dynamic",
        "canreinvite": "no",
        "nat": "force_rport,comedia",
    },
    "pjsip": {
        "context": "empleado",
        "disallow": "all",
        "allow": "ulaw",
    }
}

# HELPERS DE ENTRADA INTERACTIVA
def preguntar(mensaje: str, por_defecto: str = "") -> str:
    prompt = f"  {mensaje} [{por_defecto}]: " if por_defecto else f"  {mensaje}: "
    while True:
        respuesta = input(prompt).strip()
        if respuesta:
            return respuesta
        if por_defecto:
            return por_defecto
        print("  [!] Este campo es obligatorio.")

def preguntar_password(mensaje: str = "Contraseña", por_defecto: str = "") -> str:
    hint = " (Enter para no cambiarla)" if por_defecto else ""
    while True:
        pwd = getpass.getpass(f"  {mensaje}{hint}: ")
        if pwd:
            return pwd
        if por_defecto:
            return por_defecto
        print("  [!] La contraseña no puede estar vacía.")

def preguntar_si_no(mensaje: str, por_defecto: bool = True) -> bool:
    opciones = "S/n" if por_defecto else "s/N"
    respuesta = input(f"  {mensaje} [{opciones}]: ").strip().lower()
    if not respuesta:
        return por_defecto
    return respuesta in ("s", "si", "sí", "y", "yes")

def separador(titulo: str = "") -> None:
    linea = "─" * 50
    if titulo:
        print(f"\n{linea}")
        print(f"  {titulo.upper()}")
        print(f"{linea}")
    else:
        print(linea)

# LÓGICA DE ARCHIVOS Y SISTEMA
def reload_asterisk(protocol: str) -> None:
    """Ejecuta el comando de recarga en Asterisk según el protocolo."""
    cmd = "pjsip reload" if protocol == "pjsip" else "sip reload"
    print(f"\n  [i] Aplicando cambios en Asterisk (sudo asterisk -rx '{cmd}')...")
    try: 
        subprocess.run(["sudo", "asterisk", "-rx", cmd], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("  [✓] Asterisk recargado correctamente.")
    except subprocess.CalledProcessError:
        print("  [✗] Aviso: Hubo un problema al recargar Asterisk. Es posible que el servicio no esté corriendo.")
    except FileNotFoundError:
        print("  [✗] Aviso: No se encontró el comando 'asterisk' o 'sudo'. Recarga manual necesaria.")

def backup_conf(path: str) -> str:
    if not os.path.exists(path):
        return ""
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
        return ""

def ensure_file_structure(path: str, protocol: str) -> None:
    if not os.path.exists(path):
        print(f"  [i] {path} no encontrado. Creando nuevo archivo...")
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                if protocol == "sip":
                    f.write("[general]\nport=5060\ndirectmedia=no\nlanguage=es\ncontext=public\n\n")
                else:
                    f.write("; pjsip.conf - generado por script\n\n")
            print(f"  [✓] Archivo {path} creado correctamente.")
        except PermissionError:
            print(f"  [✗] Sin permisos para crear {path}. Ejecuta con sudo.")
            sys.exit(1)

def user_exists(path: str, username: str) -> bool:
    pattern = re.compile(rf"^\[{re.escape(username)}\]", re.MULTILINE)
    try:
        with open(path, "r") as f:
            return bool(pattern.search(f.read()))
    except FileNotFoundError:
        return False

def get_user_params(path: str, username: str, protocol: str) -> dict:
    try:
        with open(path, "r") as f:
            content = f.read()
    except FileNotFoundError:
        return {}

    params = {}
    
    sections_to_search = [username]
    if protocol == "pjsip":
        sections_to_search.extend([f"{username}-auth", f"{username}-aor", f"{username}-aors"])
        
    for section in sections_to_search:
        matches = re.finditer(rf"^\[{re.escape(section)}\](.*?)(?=^\[|\Z)", content, re.MULTILINE | re.DOTALL)
        for match in matches:
            for line in match.group(1).strip().splitlines():
                if "=" in line:
                    k, _, v = line.partition("=")
                    k, v = k.strip(), v.strip()
                    if k == "password" or k == "secret":
                        params["password"] = v
                    elif k in ["type", "context", "host", "nat", "canreinvite", "allow", "disallow"]:
                        if k == "type" and v in ["auth", "aor"]:
                            continue
                        if k not in params:
                            params[k] = v
    return params

def build_user_blocks(username: str, password: str, protocol: str, **kwargs) -> str:
    params = {**DEFAULT_PARAMS[protocol], **kwargs}
    
    if protocol == "sip":
        lines = [f"[{username}]", f"secret={password}"]
        for key in ["type", "context", "host", "nat", "canreinvite"]:
            if key in params:
                lines.append(f"{key}={params[key]}")
        return "\n".join(lines) + "\n"
    
    else: # PJSIP
        context = params.get("context", DEFAULT_PARAMS["pjsip"]["context"])
        disallow = params.get("disallow", DEFAULT_PARAMS["pjsip"]["disallow"])
        allow = params.get("allow", DEFAULT_PARAMS["pjsip"]["allow"])
        return (
            f"[{username}]\ntype=endpoint\ncontext={context}\n"
            f"disallow={disallow}\nallow={allow}\nauth={username}\naors={username}\n\n"
            f"[{username}]\ntype=auth\nauth_type=userpass\nusername={username}\npassword={password}\n\n"
            f"[{username}]\ntype=aor\nmax_contacts=1\n"
        )

def remove_user_blocks(path: str, username: str, protocol: str) -> None:
    if not os.path.exists(path): return
    with open(path, "r") as f:
        content = f.read()

    sections = [username]
    if protocol == "pjsip":
        sections.extend([f"{username}-auth", f"{username}-aor", f"{username}-aors"])

    for section in sections:
        pattern = re.compile(rf"\n?\[{re.escape(section)}\][^\[]*", re.DOTALL)
        content = pattern.sub("", content)

    with open(path, "w") as f:
        f.write(content.strip() + "\n")

def list_users(path: str) -> None:
    pattern = re.compile(r"^\[([^\]]+)\]", re.MULTILINE)
    try:
        with open(path, "r") as f:
            sections = pattern.findall(f.read())
            
        seen = set()
        users = []
        for s in sections:
            s_lower = s.lower()
            if s_lower == "general" or s.endswith("-auth") or s.endswith("-aor") or s.endswith("-aors"):
                continue
            if s not in seen:
                seen.add(s)
                users.append(s)
                
        if users:
            for u in users:
                print(f"    - {u}")
        else:
            print("  No hay usuarios configurados.")
    except FileNotFoundError:
        print(f"  [!] Archivo {path} no encontrado.")

# ─────────────────────────────────────────────
# MODO INTERACTIVO
# ─────────────────────────────────────────────
def modo_interactivo():
    print("\n╔══════════════════════════════════════════════╗")
    print("║      Gestor de usuarios SIP/PJSIP Asterisk   ║")
    print("║              Hecho por pixaisa1              ║")
    print("║                   v1.2.1                     ║")
    print("╚══════════════════════════════════════════════╝")

    separador("Selección de Protocolo")
    print("  1) PJSIP (Recomendado/Moderno)")
    print("  2) SIP (Antiguo / sip.conf)")
    
    while True:
        proto_opcion = input("\n  Elige el protocolo [1-2]: ").strip()
        if proto_opcion in ("1", "2"): break
        print("  [!] Opción no válida.")

    protocolo = "pjsip" if proto_opcion == "1" else "sip"
    ruta_por_defecto = PJSIP_CONF_PATH if protocolo == "pjsip" else SIP_CONF_PATH
    
    conf_path = preguntar(f"Ruta al archivo {protocolo}.conf", ruta_por_defecto)

    while True:
        separador(f"Gestión {protocolo.upper()} - ¿Qué quieres hacer?")
        print("  1) Agregar usuario")
        print("  2) Editar usuario")
        print("  3) Eliminar usuario")
        print("  4) Listar usuarios")
        print("  5) Salir")

        opcion = input("\n  Elige una opción [1-5]: ").strip()
        
        if opcion == "5":
            print("\n  ¡Adiós!\n")
            sys.exit(0)

        elif opcion == "4":
            separador("Usuarios existentes")
            list_users(conf_path)

        elif opcion == "3":
            separador("Eliminar usuario")
            list_users(conf_path)
            username = preguntar("Nombre del usuario a eliminar")
            if not user_exists(conf_path, username):
                print(f"  [!] El usuario '{username}' no existe.")
                continue
            if preguntar_si_no("¿Crear backup antes de eliminar?"):
                backup_conf(conf_path)
            try:
                remove_user_blocks(conf_path, username, protocolo)
                print(f"  [✓] Usuario '{username}' eliminado correctamente.")
                reload_asterisk(protocolo)
            except PermissionError:
                print(f"  [✗] Sin permisos. Ejecuta con sudo.")

        elif opcion in ("1", "2"):
            separador("Editar usuario" if opcion == "2" else "Agregar usuario")
            if opcion == "2": list_users(conf_path)
            
            username = preguntar("Nombre de usuario")
            
            if opcion == "2" and not user_exists(conf_path, username):
                print(f"  [!] El usuario '{username}' no existe.")
                continue
            elif opcion == "1" and user_exists(conf_path, username):
                print(f"  [!] El usuario '{username}' ya existe.")
                continue

            actuales = get_user_params(conf_path, username, protocolo) if opcion == "2" else {}
            
            if opcion == "2":
                print(f"\n  Editando '{username}' — Enter para conservar valor actual.")
            
            password = preguntar_password("Contraseña SIP", actuales.get("password", ""))

            separador("Parámetros avanzados")
            params = {}
            for param, default_val in DEFAULT_PARAMS[protocolo].items():
                params[param] = preguntar(param, actuales.get(param, default_val))

            if not preguntar_si_no("\n¿Confirmar y guardar?"):
                print("  Operación cancelada.")
                continue

            if preguntar_si_no("¿Deseas crear un backup antes de guardar?"):
                backup_conf(conf_path)

            try:
                ensure_file_structure(conf_path, protocolo)
                if opcion == "2":
                    remove_user_blocks(conf_path, username, protocolo)
                
                bloque = build_user_blocks(username, password, protocolo, **params)
                
                with open(conf_path, "a") as f:
                    f.write(f"\n{bloque}\n")
                print(f"  [✓] Usuario '{username}' guardado correctamente.")
                reload_asterisk(protocolo)
            except PermissionError:
                print(f"  [✗] Sin permisos para modificar el archivo. Ejecuta con sudo.")
# MODO CLI (Avanzado)
def parse_args():
    parser = argparse.ArgumentParser(description="Gestiona usuarios SIP/PJSIP en Asterisk.")
    parser.add_argument("--protocol", choices=["sip", "pjsip"], default="pjsip", help="Protocolo a usar (por defecto pjsip)")
    parser.add_argument("--conf", help="Ruta al archivo de configuración (opcional)")
    
    subparsers = parser.add_subparsers(dest="command")

    add_p = subparsers.add_parser("add", help="Agregar un usuario")
    add_p.add_argument("username")
    add_p.add_argument("password")
    
    edit_p = subparsers.add_parser("edit", help="Editar un usuario")
    edit_p.add_argument("username")
    edit_p.add_argument("password", nargs='?', default=None)

    del_p = subparsers.add_parser("delete", help="Eliminar un usuario")
    del_p.add_argument("username")

    subparsers.add_parser("list", help="Listar usuarios")

    return parser.parse_known_args()

def main():
    if len(sys.argv) == 1:
        modo_interactivo()
        return

    args, unknown = parse_args()
    
    conf_path = args.conf if args.conf else (PJSIP_CONF_PATH if args.protocol == "pjsip" else SIP_CONF_PATH)

    if args.command == "list":
        list_users(conf_path)
    
    elif args.command == "delete":
        backup_conf(conf_path)
        remove_user_blocks(conf_path, args.username, args.protocol)
        print(f"Usuario {args.username} eliminado.")
        reload_asterisk(args.protocol)

    elif args.command in ("add", "edit"):
        ensure_file_structure(conf_path, args.protocol)
        backup_conf(conf_path)
        
        params = DEFAULT_PARAMS[args.protocol].copy()
        actuales = get_user_params(conf_path, args.username, args.protocol) if args.command == "edit" else {}
        params.update(actuales)
        
        for i in range(len(unknown)):
            if unknown[i].startswith("--"):
                key = unknown[i].strip("-")
                if i + 1 < len(unknown) and not unknown[i+1].startswith("--"):
                    params[key] = unknown[i+1]

        pwd = args.password if args.password else actuales.get("password", "1234")
        
        if args.command == "edit":
            remove_user_blocks(conf_path, args.username, args.protocol)
            
        bloque = build_user_blocks(args.username, pwd, args.protocol, **params)
        with open(conf_path, "a") as f:
            f.write(f"\n{bloque}\n")
        print(f"Usuario {args.username} procesado en {conf_path}.")
        reload_asterisk(args.protocol)

if __name__ == "__main__":
    main()