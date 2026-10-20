#!/usr/bin/env python3
"""Inspect an actuator that load_actuator downloaded.

It prints the card (id, version, type, arguments), the requirements and the
source. It also checks the common local problems:

* no card.json: the venv or pip step failed, or the download is incomplete
* method.py does not define exactly one top-level function
* a requirement is installed in {name}/.venv but NOT in the interpreter that
  runs this script. run_actuator imports method.py into the current process,
  so a missing package raises ModuleNotFoundError at run time.

Run it with the same Python that runs your application:

    python inspect_actuator.py NAME [--dir nexgen_actuators] [--no-source]

The script only reads files. It never imports or runs method.py.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from importlib import metadata
from pathlib import Path


def requirement_name(line: str) -> str | None:
    """Return the distribution name of one requirements.txt line."""
    line = line.split("#", 1)[0].strip()
    if not line or line.startswith("-"):
        return None
    match = re.match(r"([A-Za-z0-9][A-Za-z0-9._-]*)", line)
    return match.group(1) if match else None


def main() -> int:
    """Print the report. Return 1 if a problem is found."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("name", help="actuator name (directory under --dir)")
    parser.add_argument(
        "--dir", default="nexgen_actuators", help="actuators_dir (default: %(default)s)"
    )
    parser.add_argument(
        "--no-source", action="store_true", help="do not print method.py"
    )
    args = parser.parse_args()

    root = Path(args.dir) / args.name
    problems: list[str] = []

    if not root.is_dir():
        print(f"{root} does not exist. Call load_actuator({args.name!r}) first.")
        return 1

    print(f"Actuator directory: {root.resolve()}")
    print(f"Interpreter:        {sys.executable}")

    card_path = root / "card.json"
    if card_path.is_file():
        card = json.loads(card_path.read_text(encoding="utf-8"))
        print("\n== card.json")
        for key in ("id", "name", "version", "actuator_type", "latest", "updated_at"):
            print(f"  {key:14} {card.get(key)}")
        method_args = card.get("method_args") or {}
        if method_args:
            print("  arguments:")
            for arg, spec in method_args.items():
                spec = spec or {}
                default = spec.get("default")
                suffix = "" if default is None else f" = {default}"
                print(f"    {arg}: {spec.get('type')}{suffix}")
        if card.get("latest") is False:
            problems.append(
                "card.json says latest=false. The server accepts data items only "
                "from the latest version. Run load_actuator again."
            )
    else:
        problems.append(
            "card.json is missing. The venv or pip step probably failed. The next "
            "load_actuator call downloads the actuator again."
        )

    method_path = root / "method.py"
    source = ""
    if method_path.is_file():
        source = method_path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
            funcs = [
                n.name
                for n in tree.body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
            if len(funcs) != 1:
                problems.append(
                    f"method.py defines {len(funcs)} top-level functions "
                    f"({', '.join(funcs) or 'none'}). run_actuator needs exactly one."
                )
        except SyntaxError as exc:
            problems.append(f"method.py has a syntax error: {exc}")
    else:
        problems.append("method.py is missing.")

    req_path = root / "requirements.txt"
    print("\n== requirements (checked in the current interpreter)")
    lines = req_path.read_text(encoding="utf-8").splitlines() if req_path.is_file() else []
    names = [(line.strip(), requirement_name(line)) for line in lines]
    names = [(line, name) for line, name in names if name]
    if not names:
        print("  (none)")
    for line, name in names:
        try:
            version = metadata.version(name)
            print(f"  ok       {line}  (installed: {version})")
        except metadata.PackageNotFoundError:
            print(f"  MISSING  {line}")
            problems.append(
                f"{name} is not installed in {sys.executable}. run_actuator does "
                f"not use {root / '.venv'}. Run: {sys.executable} -m pip install "
                f"{line!r}"
            )

    if not (root / ".venv").is_dir():
        print("\n  note: .venv is missing")

    if source and not args.no_source:
        print("\n== method.py")
        print(source.rstrip())

    print()
    if problems:
        print("Problems:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("No problems found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
