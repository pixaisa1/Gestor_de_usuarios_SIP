#!/usr/bin/env python3
import os
import sys
import argparse
import re
import getpass
import subprocess
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURACIÓN Y CONSTANTES
# ─────────────────────────────────────────────
SIP_CONF_PATH = "/etc/asterisk/sip.conf"
PJSIP_CONF_PATH = "/etc/asterisk/pjsip.conf"
EXTENSIONS_CONF_PATH = "/etc/asterisk/extensions.conf"
BACKUP_SUFFIX = ".bak"

DEFAULT_PARAMS = {
    "sip": {
        "type": "friend",
        "context": "from-internal",
        "host": "dynamic",
        "canreinvite": "no",
        "nat": "force_rport,comedia",
    },
    "pjsip": {
        "context": "from-internal",
        "disallow": "all",
        "allow": "ulaw",
    }
}

# ─────────────────────────────────────────────
# HELPERS DE ENTRADA INTERACTIVA
# ─────────────────────────────────────────────
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
    linea = "─" * 55
    if titulo:
        print(f"\n{linea}")
        print(f"  {titulo.upper()}")
        print(f"{linea}")
    else:
        print(linea)

# ─────────────────────────────────────────────
# LÓGICA DE SISTEMA Y BACKUP
# ─────────────────────────────────────────────
def reload_asterisk(modulo: str) -> None:
    """Ejecuta el comando de recarga en Asterisk."""
    if modulo == "pjsip": cmd = "pjsip reload"
    elif modulo == "sip": cmd = "sip reload"
    elif modulo == "dialplan": cmd = "dialplan reload"
    else: return

    print(f"\n  [i] Aplicando cambios en Asterisk (sudo asterisk -rx '{cmd}')...")
    try:
        subprocess.run(["sudo", "asterisk", "-rx", cmd], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("  [✓] Asterisk recargado correctamente.")
    except subprocess.CalledProcessError:
        print("  [✗] Aviso: Hubo un problema al recargar Asterisk. ¿Está el servicio corriendo?")
    except FileNotFoundError:
        print("  [✗] Aviso: Comando 'asterisk' o 'sudo' no encontrado.")

def backup_conf(path: str) -> str:
    if not os.path.exists(path): return ""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{path}{BACKUP_SUFFIX}.{timestamp}"
    try:
        with open(path, "r") as original: content = original.read()
        with open(backup_path, "w") as backup: backup.write(content)
        print(f"  [✓] Backup creado: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"  [!] No se pudo crear backup: {e}")
        return ""

def ensure_file_structure(path: str, tipo: str) -> None:
    if not os.path.exists(path):
        print(f"  [i] {path} no encontrado. Creando nuevo archivo...")
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                if tipo == "sip": f.write("[general]\nport=5060\ndirectmedia=no\ncontext=public\n\n")
                elif tipo == "extensions": f.write("; extensions.conf\n\n[from-internal]\n")
                else: f.write("; pjsip.conf\n\n")
            print(f"  [✓] Archivo {path} creado correctamente.")
        except PermissionError:
            print(f"  [✗] Sin permisos para crear {path}. Ejecuta con sudo.")
            sys.exit(1)

# ─────────────────────────────────────────────
# LÓGICA DE USUARIOS (SIP/PJSIP)
# ─────────────────────────────────────────────
def user_exists(path: str, username: str) -> bool:
    try:
        with open(path, "r") as f: return bool(re.search(rf"^\[{re.escape(username)}\]", f.read(), re.MULTILINE))
    except FileNotFoundError: return False

def get_user_params(path: str, username: str, protocol: str) -> dict:
    try:
        with open(path, "r") as f: content = f.read()
    except FileNotFoundError: return {}
    params = {}
    sections = [username]
    if protocol == "pjsip": sections.extend([f"{username}-auth", f"{username}-aor", f"{username}-aors"])
        
    for section in sections:
        for match in re.finditer(rf"^\[{re.escape(section)}\](.*?)(?=^\[|\Z)", content, re.MULTILINE | re.DOTALL):
            for line in match.group(1).strip().splitlines():
                if "=" in line:
                    k, _, v = line.partition("=")
                    k, v = k.strip(), v.strip()
                    if k in ("password", "secret"): params["password"] = v
                    elif k in ["type", "context", "host", "nat", "canreinvite", "allow", "disallow"]:
                        if k == "type" and v in ["auth", "aor"]: continue
                        if k not in params: params[k] = v
    return params

def build_user_blocks(username: str, password: str, protocol: str, **kwargs) -> str:
    params = {**DEFAULT_PARAMS[protocol], **kwargs}
    if protocol == "sip":
        lines = [f"[{username}]", f"secret={password}"]
        for key in ["type", "context", "host", "nat", "canreinvite"]:
            if key in params: lines.append(f"{key}={params[key]}")
        return "\n".join(lines) + "\n"
    else:
        ctx, dis, allw = params.get("context"), params.get("disallow"), params.get("allow")
        return (
            f"[{username}]\ntype=endpoint\ncontext={ctx}\ndisallow={dis}\nallow={allw}\n"
            f"auth={username}\naors={username}\n\n"
            f"[{username}]\ntype=auth\nauth_type=userpass\nusername={username}\npassword={password}\n\n"
            f"[{username}]\ntype=aor\nmax_contacts=1\n"
        )

def remove_user_blocks(path: str, username: str, protocol: str) -> None:
    if not os.path.exists(path): return
    with open(path, "r") as f: content = f.read()
    sections = [username]
    if protocol == "pjsip": sections.extend([f"{username}-auth", f"{username}-aor", f"{username}-aors"])
    for section in sections:
        content = re.sub(rf"\n?\[{re.escape(section)}\][^\[]*", "", content, flags=re.DOTALL)
    with open(path, "w") as f: f.write(content.strip() + "\n")

def list_users(path: str, protocol: str) -> None:
    """Lista los usuarios en formato tabla con su número y contexto."""
    try:
        with open(path, "r") as f: sections = re.findall(r"^\[([^\]]+)\]", f.read(), re.MULTILINE)
        seen = set()
        users = []
        for s in sections:
            s_lower = s.lower()
            if s_lower == "general" or s.endswith(("-auth", "-aor", "-aors")): continue
            if s not in seen:
                seen.add(s)
                # Obtenemos los parámetros del usuario para sacar su contexto
                params = get_user_params(path, s, protocol)
                ctx = params.get("context", "desconocido")
                users.append((s, ctx))
                
        if users:
            print(f"    {'USUARIO / NÚMERO'.ljust(20)} │ {'GRUPO (CONTEXTO)'.ljust(25)}")
            print(f"    {'─'*20}─┼─{'─'*25}")
            for u, ctx in users:
                print(f"    {u.ljust(20)} │ {ctx.ljust(25)}")
            print() # Salto de línea por estética
        else:
            print("  No hay usuarios configurados.")
    except FileNotFoundError:
        print(f"  [!] Archivo {path} no encontrado.")

# ─────────────────────────────────────────────
# LÓGICA DE EXTENSIONES (DIALPLAN)
# ─────────────────────────────────────────────
def remove_extension(path: str, exten: str) -> None:
    if not os.path.exists(path): return
    with open(path, "r") as f: lines = f.readlines()
    with open(path, "w") as f:
        for line in lines:
            if line.strip().startswith(f"exten => {exten},") or line.strip().startswith(f"exten=>{exten},"):
                continue
            f.write(line)

def add_extension(path: str, context: str, exten: str, endpoint: str, protocol: str) -> None:
    remove_extension(path, exten) # Limpia si ya existe
    ensure_file_structure(path, "extensions")
    
    with open(path, "r") as f: content = f.read()
    
    line1 = f"exten => {exten},1,Dial({protocol.upper()}/{endpoint},30)"
    line2 = f"exten => {exten},2,Hangup()"
    
    if f"[{context}]" in content:
        # Inserta justo debajo del nombre del contexto
        content = content.replace(f"[{context}]", f"[{context}]\n{line1}\n{line2}", 1)
        with open(path, "w") as f: f.write(content)
    else:
        # Añade el contexto al final si no existe
        with open(path, "a") as f: f.write(f"\n[{context}]\n{line1}\n{line2}\n")

def list_extensions(path: str) -> None:
    try:
        with open(path, "r") as f: lines = f.readlines()
        current_ctx = None
        count = 0
        for line in lines:
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                current_ctx = line
            elif line.startswith("exten =>") and ",1,Dial" in line:
                try:
                    ext = line.split("=>")[1].split(",")[0].strip()
                    dest = line.split("Dial(")[1].split(",")[0].strip()
                    print(f"    {current_ctx.ljust(20)} Ext: {ext.ljust(8)} -> Llama a: {dest}")
                    count += 1
                except IndexError: pass
        if count == 0: print("  No hay extensiones configuradas de forma explícita.")
        print()
    except FileNotFoundError: print(f"  [!] Archivo {path} no encontrado.")

# ─────────────────────────────────────────────
# MENÚS INTERACTIVOS
# ─────────────────────────────────────────────
def menu_usuarios():
    separador("Selección de Protocolo de Usuario")
    print("  1) PJSIP (Recomendado/Moderno)")
    print("  2) SIP (Antiguo / sip.conf)")
    
    while True:
        proto_opc = input("\n  Elige el protocolo [1-2]: ").strip()
        if proto_opc in ("1", "2"): break
        print("  [!] Opción no válida.")

    protocolo = "pjsip" if proto_opc == "1" else "sip"
    conf_path = preguntar(f"Ruta al archivo {protocolo}.conf", PJSIP_CONF_PATH if protocolo == "pjsip" else SIP_CONF_PATH)

    while True:
        separador(f"Gestión {protocolo.upper()} - ¿Qué quieres hacer?")
        print("  1) Agregar usuario")
        print("  2) Editar usuario")
        print("  3) Eliminar usuario")
        print("  4) Listar usuarios")
        print("  5) Volver al menú principal")

        opcion = input("\n  Opción [1-5]: ").strip()
        
        if opcion == "5": return
        elif opcion == "4":
            separador("Usuarios existentes")
            list_users(conf_path, protocolo)
        elif opcion == "3":
            separador("Eliminar usuario")
            list_users(conf_path, protocolo)
            username = preguntar("Nombre del usuario a eliminar")
            if not user_exists(conf_path, username):
                print(f"  [!] El usuario '{username}' no existe.")
                continue
            if preguntar_si_no("¿Crear backup antes de eliminar?"): backup_conf(conf_path)
            try:
                remove_user_blocks(conf_path, username, protocolo)
                print(f"  [✓] Usuario '{username}' eliminado.")
                reload_asterisk(protocolo)
            except PermissionError: print(f"  [✗] Sin permisos. Usa sudo.")
        elif opcion in ("1", "2"):
            separador("Editar usuario" if opcion == "2" else "Agregar usuario")
            if opcion == "2": list_users(conf_path, protocolo)
            username = preguntar("Nombre de usuario")
            
            if opcion == "2" and not user_exists(conf_path, username):
                print(f"  [!] El usuario '{username}' no existe."); continue
            elif opcion == "1" and user_exists(conf_path, username):
                print(f"  [!] El usuario '{username}' ya existe."); continue

            actuales = get_user_params(conf_path, username, protocolo) if opcion == "2" else {}
            password = preguntar_password("Contraseña SIP", actuales.get("password", ""))

            separador("Parámetros avanzados")
            params = {}
            for param, default_val in DEFAULT_PARAMS[protocolo].items():
                params[param] = preguntar(param, actuales.get(param, default_val))

            if not preguntar_si_no("\n¿Confirmar y guardar?"): continue
            if preguntar_si_no("¿Backup antes de guardar?"): backup_conf(conf_path)

            try:
                ensure_file_structure(conf_path, protocolo)
                if opcion == "2": remove_user_blocks(conf_path, username, protocolo)
                bloque = build_user_blocks(username, password, protocolo, **params)
                with open(conf_path, "a") as f: f.write(f"\n{bloque}\n")
                print(f"  [✓] Usuario '{username}' guardado.")
                reload_asterisk(protocolo)
            except PermissionError: print(f"  [✗] Sin permisos. Usa sudo.")

def menu_extensiones():
    conf_path = preguntar("Ruta al archivo extensions.conf", EXTENSIONS_CONF_PATH)
    while True:
        separador("Gestión de EXTENSIONES (Dialplan)")
        print("  1) Asignar / Editar extensión a un usuario")
        print("  2) Eliminar extensión")
        print("  3) Listar extensiones")
        print("  4) Volver al menú principal")

        opcion = input("\n  Opción [1-4]: ").strip()
        
        if opcion == "4": return
        elif opcion == "3":
            separador("Extensiones configuradas")
            list_extensions(conf_path)
        elif opcion == "2":
            separador("Eliminar extensión")
            exten = preguntar("Número de extensión a eliminar (ej. 100)")
            if preguntar_si_no("¿Crear backup antes de eliminar?"): backup_conf(conf_path)
            try:
                remove_extension(conf_path, exten)
                print(f"  [✓] Extensión {exten} eliminada.")
                reload_asterisk("dialplan")
            except PermissionError: print("  [✗] Sin permisos. Usa sudo.")
        elif opcion == "1":
            separador("Nueva Extensión")
            exten = preguntar("Número de extensión (ej. 100)")
            endpoint = preguntar("Nombre del usuario/endpoint al que llamará (ej. pedro)")
            proto = preguntar("¿Protocolo del usuario? (PJSIP o SIP)", "PJSIP")
            contexto = preguntar("Contexto donde ubicarla", "from-internal")
            
            if not preguntar_si_no("\n¿Confirmar y guardar?"): continue
            if preguntar_si_no("¿Backup antes de guardar?"): backup_conf(conf_path)
            
            try:
                add_extension(conf_path, contexto, exten, endpoint, proto)
                print(f"  [✓] Extensión {exten} asignada a {proto.upper()}/{endpoint}.")
                reload_asterisk("dialplan")
            except PermissionError: print("  [✗] Sin permisos. Usa sudo.")

def modo_interactivo():
    print("\n╔══════════════════════════════════════════════╗")
    print("║      Gestor Integral de Asterisk v2.2        ║")
    print("║              Hecho por pixaisa1              ║")
    print("╚══════════════════════════════════════════════╝")

    while True:
        separador("MENÚ PRINCIPAL")
        print("  1) Gestionar Usuarios (PJSIP / SIP)")
        print("  2) Gestionar Extensiones (extensions.conf)")
        print("  3) Salir del programa")
        
        opc = input("\n  Elige una opción [1-3]: ").strip()
        
        if opc == "1":
            menu_usuarios()
        elif opc == "2":
            menu_extensiones()
        elif opc == "3":
            print("\n  ¡Adiós!\n")
            sys.exit(0)
        else:
            print("  [!] Opción no válida.")

# ─────────────────────────────────────────────
# MODO CLI (Avanzado)
# ─────────────────────────────────────────────
def parse_args():
    # Argumentos globales
    base_parser = argparse.ArgumentParser(add_help=False)
    base_parser.add_argument("--no-backup", action="store_true", help="No crear copia de seguridad (.bak)")
    base_parser.add_argument("--no-reload", action="store_true", help="No recargar Asterisk tras guardar")

    parser = argparse.ArgumentParser(description="Gestor Integral de Asterisk - Modo CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Comandos de Usuarios
    u_add = subparsers.add_parser("add-user", parents=[base_parser], help="Añadir un usuario SIP/PJSIP")
    u_add.add_argument("username")
    u_add.add_argument("password")
    u_add.add_argument("--protocol", choices=["sip", "pjsip"], default="pjsip")

    u_edit = subparsers.add_parser("edit-user", parents=[base_parser], help="Editar un usuario existente")
    u_edit.add_argument("username")
    u_edit.add_argument("--password", default=None)
    u_edit.add_argument("--protocol", choices=["sip", "pjsip"], default="pjsip")

    u_del = subparsers.add_parser("del-user", parents=[base_parser], help="Eliminar un usuario")
    u_del.add_argument("username")
    u_del.add_argument("--protocol", choices=["sip", "pjsip"], default="pjsip")

    u_list = subparsers.add_parser("list-users", help="Listar usuarios")
    u_list.add_argument("--protocol", choices=["sip", "pjsip"], default="pjsip")

    # Comandos de Extensiones
    e_add = subparsers.add_parser("add-exten", parents=[base_parser], help="Asignar extensión a un usuario")
    e_add.add_argument("exten", help="Número de extensión (ej. 100)")
    e_add.add_argument("endpoint", help="Nombre del usuario a llamar")
    e_add.add_argument("--protocol", choices=["sip", "pjsip"], default="pjsip")
    e_add.add_argument("--context", default="from-internal", help="Contexto de dialplan")

    e_del = subparsers.add_parser("del-exten", parents=[base_parser], help="Eliminar una extensión")
    e_del.add_argument("exten")

    e_list = subparsers.add_parser("list-extens", help="Listar extensiones configuradas")

    return parser.parse_known_args()

def main():
    if len(sys.argv) == 1:
        modo_interactivo()
        return

    args, unknown = parse_args()
    if not args.command:
        modo_interactivo()
        return

    # Bloque de comandos para Usuarios
    if args.command in ("add-user", "edit-user", "del-user", "list-users"):
        conf_path = PJSIP_CONF_PATH if args.protocol == "pjsip" else SIP_CONF_PATH

        if args.command == "list-users":
            list_users(conf_path, args.protocol)
            return

        if args.command == "del-user":
            if not args.no_backup: backup_conf(conf_path)
            remove_user_blocks(conf_path, args.username, args.protocol)
            print(f"  [✓] Usuario {args.username} eliminado correctamente.")
            if not args.no_reload: reload_asterisk(args.protocol)
            return

        # Para Add o Edit
        ensure_file_structure(conf_path, args.protocol)
        if not args.no_backup: backup_conf(conf_path)

        params = DEFAULT_PARAMS[args.protocol].copy()
        actuales = get_user_params(conf_path, args.username, args.protocol) if args.command == "edit-user" else {}
        params.update(actuales)

        # Captura argumentos extra avanzados por consola (ej. --context ventas)
        for i in range(len(unknown)):
            if unknown[i].startswith("--"):
                k = unknown[i].strip("-")
                if i + 1 < len(unknown) and not unknown[i+1].startswith("--"):
                    params[k] = unknown[i+1]

        pwd = args.password if hasattr(args, "password") and args.password else actuales.get("password", "1234")

        if args.command == "edit-user":
            remove_user_blocks(conf_path, args.username, args.protocol)

        bloque = build_user_blocks(args.username, pwd, args.protocol, **params)
        with open(conf_path, "a") as f: f.write(f"\n{bloque}\n")
        print(f"  [✓] Usuario {args.username} guardado exitosamente.")
        if not args.no_reload: reload_asterisk(args.protocol)

    # Bloque de comandos para Extensiones
    elif args.command in ("add-exten", "del-exten", "list-extens"):
        conf_path = EXTENSIONS_CONF_PATH

        if args.command == "list-extens":
            list_extensions(conf_path)
            return

        if args.command == "del-exten":
            if not args.no_backup: backup_conf(conf_path)
            remove_extension(conf_path, args.exten)
            print(f"  [✓] Extensión {args.exten} eliminada.")
            if not args.no_reload: reload_asterisk("dialplan")
            return

        # Para Add Exten
        if not args.no_backup: backup_conf(conf_path)
        add_extension(conf_path, args.context, args.exten, args.endpoint, args.protocol)
        print(f"  [✓] Extensión {args.exten} asignada hacia {args.protocol.upper()}/{args.endpoint}.")
        if not args.no_reload: reload_asterisk("dialplan")

if __name__ == "__main__":
    main()