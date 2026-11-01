#!/usr/bin/env python3
"""User-only desktop integration for a separately downloaded BedrockOnLinux AppImage."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import tempfile

PROJECT = "bedrock-desktop-setup"
VERSION = 1


def xdg(name, fallback):
    p = Path(os.environ.get(name) or str(Path.home() / fallback))
    if not p.is_absolute():
        raise ValueError(name + " must be an absolute path")
    return p


def locations():
    data = xdg("XDG_DATA_HOME", ".local/share")
    state = xdg("XDG_STATE_HOME", ".local/state") / PROJECT
    return {
        "game_script": Path.home() / ".local/bin/bedrock-desktop-game",
        "launcher_script": Path.home() / ".local/bin/bedrock-desktop-launcher",
        "game_entry": data / "applications/bedrock-desktop-game.desktop",
        "launcher_entry": data / "applications/bedrock-desktop-launcher.desktop",
        "icon": data / PROJECT / "icon.svg",
        "manifest": data / PROJECT / "installed.json",
        "logs": state / "logs",
    }


def digest(data):
    return hashlib.sha256(data).hexdigest()


def atomic(path, data, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".bedrock-setup-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def read_manifest(paths):
    p = paths["manifest"]
    if p.is_symlink():
        raise ValueError("Refusing a symlinked installation manifest")
    if not p.exists():
        return None
    record = json.loads(p.read_text())
    if record.get("project") != PROJECT or record.get("version") != VERSION:
        raise ValueError("Unknown installation manifest")
    return record


def check_owned(paths, old, keys):
    for key in keys:
        p = paths[key]
        if p.is_symlink():
            raise ValueError("Refusing to overwrite/remove a symlink: " + str(p))
        if p.exists():
            expected = (old or {}).get("files", {}).get(key)
            if not p.is_file() or expected != digest(p.read_bytes()):
                raise ValueError("Unmanaged or modified file; left untouched: " + str(p))


def desktop_quote(value):
    value = str(value)
    escaped = "".join("\\" + c if c in "\\\"`$" else c for c in value)
    return "\"" + escaped.replace("\\", "\\\\") + "\""


def make_files(paths, app):
    for p in [app, *paths.values()]:
        if any(c in str(p) for c in "\n\r\x00"):
            raise ValueError("Control characters in paths are not supported")
    files = {}
    for kind, mode, title in (
        ("game", "play", "Minecraft Bedrock"),
        ("launcher", "gui", "Minecraft Bedrock Launcher"),
    ):
        log = paths["logs"] / (kind + ".log")
        script = (
            "#!/bin/sh\n# Managed by bedrock-desktop-setup\numask 077\n"
            + "mkdir -p " + shlex.quote(str(paths["logs"])) + " || exit 1\n"
            + "exec /usr/bin/env -u LD_PRELOAD -u LD_LIBRARY_PATH "
            + shlex.quote(str(app)) + " " + mode
            + " >> " + shlex.quote(str(log)) + " 2>&1\n"
        )
        entry = (
            "[Desktop Entry]\nType=Application\nName=" + title
            + "\nComment=Unofficial BedrockOnLinux desktop integration"
            + "\nExec=" + desktop_quote(paths[kind + "_script"])
            + "\nIcon=" + str(paths["icon"]).replace("\\", "\\\\")
            + "\nTerminal=false\nStartupNotify=false\nCategories=Game;\n"
        )
        files[kind + "_script"] = (script.encode(), 0o755)
        files[kind + "_entry"] = (entry.encode(), 0o644)
    icon = Path(__file__).resolve().parent / "assets/bedrock.svg"
    files["icon"] = (icon.read_bytes(), 0o644)
    return files


def install(app):
    app = app.expanduser().resolve(strict=True)
    if not app.is_file() or not os.access(app, os.X_OK):
        raise ValueError("AppImage must be a file with executable permission (chmod +x)")
    paths = locations()
    old = read_manifest(paths)
    files = make_files(paths, app)
    check_owned(paths, old, files)
    record = {"project": PROJECT, "version": VERSION, "appimage": str(app),
              "files": {k: digest(data) for k, (data, _) in files.items()}}
    writes = dict(files)
    writes["manifest"] = ((json.dumps(record, indent=2) + "\n").encode(), 0o600)
    before = {k: (paths[k].read_bytes(), paths[k].stat().st_mode & 0o777)
              if paths[k].exists() else None for k in writes}
    try:
        for key, (data, mode) in writes.items():
            atomic(paths[key], data, mode)
    except BaseException:
        for key, previous in before.items():
            if previous is None:
                paths[key].unlink(missing_ok=True)
            else:
                atomic(paths[key], *previous)
        raise
    print("Installed: Minecraft Bedrock / Minecraft Bedrock Launcher")
    print("AppImage:", app)
    print("Logs:", paths["logs"])
    print("Reopen your application menu. Existing launchers were not changed.")


def uninstall():
    paths = locations()
    old = read_manifest(paths)
    if old is None:
        print("No installation record; nothing removed.")
        return
    keys = ("game_script", "launcher_script", "game_entry", "launcher_entry", "icon")
    check_owned(paths, old, keys)
    for key in keys:
        paths[key].unlink(missing_ok=True)
    paths["manifest"].unlink()
    print("Integration removed. AppImage, Minecraft, accounts, worlds and logs kept.")


def main():
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        raise SystemExit("Run as your normal desktop user, not with sudo.")
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    setup = commands.add_parser("install", help="Create/update two menu entries")
    setup.add_argument("appimage", type=Path)
    commands.add_parser("uninstall", help="Remove only unchanged managed files")
    commands.add_parser("status", help="Show the integration installation record")
    args = parser.parse_args()
    try:
        if args.command == "install":
            install(args.appimage)
        elif args.command == "uninstall":
            uninstall()
        else:
            record = read_manifest(locations())
            print(json.dumps(record, indent=2) if record else "Not installed")
    except (OSError, ValueError) as exc:
        parser.exit(1, "Error: " + str(exc) + "\n")


if __name__ == "__main__":
    main()
