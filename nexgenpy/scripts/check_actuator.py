#!/usr/bin/env python3
"""Statically check nexgenpy actuator functions before they are registered.

The server stores only the function source (from the `def` line to the end of
the body), and the client runs it alone in `method.py`. This script finds the
actuators in a file and reports what would break after the download:

* names the function uses but never defines (module-level imports, constants,
  helpers): a NameError at run time
* positional-only or *args parameters (run_actuator calls `func(**data)`)
* `global` / `nonlocal` statements
* invalid or missing @actuator arguments
* third-party imports that are missing from `requirements`, and unpinned
  requirements
* a module-level registration call with no `if __name__ == "__main__":` guard

It finds actuators in two forms:

    @actuator(name=..., atype=..., ...)
    def f(...): ...

    publish = actuator(name=..., ...)(f)

Usage:
    python check_actuator.py FILE.py [FILE.py ...]

The exit code is 1 if any check reports an error, else 0. The script only
parses the code. It never imports or runs it.
"""

from __future__ import annotations

import argparse
import ast
import builtins
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

DECORATOR_PARAMS = ["name", "atype", "version", "is_latest", "requirements"]
BUILTIN_NAMES = set(dir(builtins)) | {"__file__", "__name__", "__builtins__"}
STDLIB = set(getattr(sys, "stdlib_module_names", ())) | {"__future__"}

# Import name -> pip distribution name, for packages where the two differ.
IMPORT_TO_DIST = {
    "PIL": "pillow",
    "cv2": "opencv-python",
    "sklearn": "scikit-learn",
    "skimage": "scikit-image",
    "yaml": "pyyaml",
    "bs4": "beautifulsoup4",
    "dateutil": "python-dateutil",
    "Crypto": "pycryptodome",
    "attr": "attrs",
    "google": "protobuf",
    "jwt": "pyjwt",
    "dotenv": "python-dotenv",
    "serial": "pyserial",
    "usb": "pyusb",
    "magic": "python-magic",
    "fitz": "pymupdf",
    "docx": "python-docx",
    "pptx": "python-pptx",
    "sentencepiece": "sentencepiece",
    "tensorflow": "tensorflow",
    "torchvision": "torchvision",
    "torchaudio": "torchaudio",
}
# Alternative distributions that also provide the import.
DIST_ALTERNATIVES = {
    "opencv-python": {
        "opencv-python-headless",
        "opencv-contrib-python",
        "opencv-contrib-python-headless",
    },
    "tensorflow": {"tensorflow-cpu", "tensorflow-gpu", "tf-nightly"},
    "pillow": {"pillow-simd"},
}


@dataclass
class Report:
    """Findings for one actuator."""

    label: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def normalize_dist(name: str) -> str:
    """Normalize a distribution name as PEP 503 does."""
    return re.sub(r"[-_.]+", "-", name).lower()


def is_actuator_factory(node: ast.AST) -> bool:
    """Return True for `actuator(...)` or `<module>.actuator(...)` calls."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Name):
        return func.id == "actuator"
    if isinstance(func, ast.Attribute):
        return func.attr == "actuator"
    return False


def module_level_bindings(tree: ast.Module) -> dict[str, str]:
    """Map each name bound at module level to the kind of binding."""
    kinds: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                bound = alias.asname or alias.name.split(".")[0]
                kinds[bound] = "a module-level import"
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            kinds[node.name] = "a module-level function"
        elif isinstance(node, ast.ClassDef):
            kinds[node.name] = "a module-level class"
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                for sub in ast.walk(target):
                    if isinstance(sub, ast.Name):
                        kinds[sub.id] = "a module-level variable"
    return kinds


def bound_names(func: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    """Collect every name bound anywhere inside the function (flow-insensitive)."""
    bound: set[str] = {func.name}
    for node in ast.walk(func):
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            bound.add(node.id)
        elif isinstance(node, ast.arg):
            bound.add(node.arg)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if alias.name != "*":
                    bound.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ExceptHandler) and node.name:
            bound.add(node.name)
        elif isinstance(node, (ast.MatchAs, ast.MatchStar)) and node.name:
            bound.add(node.name)
        elif isinstance(node, ast.MatchMapping) and node.rest:
            bound.add(node.rest)
        for param in getattr(node, "type_params", None) or []:
            bound.add(param.name)
    return bound


def check_free_names(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
    module_kinds: dict[str, str],
    report: Report,
) -> None:
    """Report names that will not exist when method.py runs alone."""
    bound = bound_names(func)
    # Names in the decorator list are not part of the uploaded source.
    scanned = [*func.body, func.args]
    if func.returns is not None:
        scanned.append(func.returns)
    seen: dict[str, int] = {}
    for root in scanned:
        for node in ast.walk(root):
            if (
                isinstance(node, ast.Name)
                and isinstance(node.ctx, ast.Load)
                and node.id not in bound
                and node.id not in BUILTIN_NAMES
            ):
                seen.setdefault(node.id, node.lineno)
    for name, line in sorted(seen.items(), key=lambda item: item[1]):
        kind = module_kinds.get(name)
        if kind:
            report.errors.append(
                f"line {line}: `{name}` is {kind}. It is not uploaded, so the "
                f"actuator raises NameError. Move it into the function body."
            )
        else:
            report.errors.append(
                f"line {line}: `{name}` is not defined in the function. The "
                f"actuator raises NameError at run time."
            )


def check_signature(
    func: ast.FunctionDef | ast.AsyncFunctionDef, report: Report
) -> None:
    """Report parameters that cannot receive values from `func(**data)`."""
    args = func.args
    if args.posonlyargs:
        names = ", ".join(a.arg for a in args.posonlyargs)
        report.errors.append(
            f"positional-only parameters ({names}) cannot get values, because "
            f"run_actuator calls func(**data). Remove the `/`."
        )
    if args.vararg:
        report.warnings.append(
            f"`*{args.vararg.arg}` never gets a value from func(**data)."
        )
    if isinstance(func, ast.AsyncFunctionDef):
        report.warnings.append(
            "`async def` returns a coroutine. run_actuator and Actuator.run do "
            "not await the function. Use a plain `def` (Actuator.arun already "
            "runs it in a thread)."
        )
    for node in ast.walk(func):
        if isinstance(node, (ast.Global, ast.Nonlocal)):
            keyword = "global" if isinstance(node, ast.Global) else "nonlocal"
            report.errors.append(
                f"line {node.lineno}: `{keyword}` refers to state outside the "
                f"function, and that state is not uploaded."
            )
    has_annotations = any(
        a.annotation is not None
        for a in [*args.posonlyargs, *args.args, *args.kwonlyargs]
    )
    if not has_annotations and (args.args or args.kwonlyargs):
        report.notes.append(
            "no parameter type hints. They go to the server as method_args and "
            "help callers."
        )


def literal(node: ast.AST) -> tuple[bool, object]:
    """Return (True, value) if node is a literal, else (False, None)."""
    try:
        return True, ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
        return False, None


def check_decorator_args(call: ast.Call, report: Report) -> list[str] | None:
    """Validate the @actuator arguments. Return the requirements if they are literal."""
    given: dict[str, ast.AST] = {}
    for param, arg in zip(DECORATOR_PARAMS, call.args, strict=False):
        given[param] = arg
    for kw in call.keywords:
        if kw.arg is None:
            report.notes.append("`**kwargs` in @actuator(...): arguments not checked.")
            return None
        if kw.arg not in DECORATOR_PARAMS:
            report.errors.append(f"@actuator has no parameter `{kw.arg}`.")
        given[kw.arg] = kw.value

    missing = [p for p in DECORATOR_PARAMS if p not in given]
    if missing:
        report.errors.append(
            f"@actuator is missing required arguments: {', '.join(missing)} "
            f"(none of the five have defaults)."
        )

    requirements: list[str] | None = None
    for param, node in given.items():
        ok, value = literal(node)
        if not ok:
            if param == "requirements":
                report.notes.append(
                    "requirements is not a literal, so imports were not compared "
                    "with it."
                )
            continue
        if param == "name":
            if not isinstance(value, str):
                report.errors.append("name must be a str.")
            elif (
                not value
                or value in {".", ".."}
                or "/" in value
                or "\\" in value
                or Path(value).name != value
            ):
                report.errors.append(
                    f"name {value!r} is not a plain directory name. load_actuator "
                    f"rejects it."
                )
            else:
                report.label = f"{report.label} [{value}]"
        elif param == "atype" and value not in ("coding", "decoding"):
            report.errors.append(f"atype must be 'coding' or 'decoding', not {value!r}.")
        elif param == "version" and not isinstance(value, str):
            report.errors.append(
                f"version must be a str, for example '1.0.0', not {value!r}."
            )
        elif param == "is_latest" and not isinstance(value, bool):
            report.errors.append(f"is_latest must be a bool, not {value!r}.")
        elif param == "requirements":
            if value is None:
                requirements = []
            elif isinstance(value, list) and all(isinstance(r, str) for r in value):
                requirements = value
            else:
                report.errors.append("requirements must be None or a list of str.")
    return requirements


def check_requirements(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
    requirements: list[str],
    report: Report,
) -> None:
    """Compare the third-party imports in the body with `requirements`."""
    declared = set()
    for req in requirements:
        match = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)", req)
        if match:
            declared.add(normalize_dist(match.group(1)))
        if not re.search(r"==|===|@", req):
            report.notes.append(
                f"requirement {req!r} is not pinned. Pin it (e.g. 'pkg==1.2.3') "
                f"so that every client installs the same code."
            )

    imported: dict[str, int] = {}
    for node in ast.walk(func):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.setdefault(alias.name.split(".")[0], node.lineno)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imported.setdefault(node.module.split(".")[0], node.lineno)

    for module, line in sorted(imported.items(), key=lambda item: item[1]):
        if module in STDLIB or module == "nexgenpy":
            continue
        dist = normalize_dist(IMPORT_TO_DIST.get(module, module))
        candidates = {dist} | {
            normalize_dist(d) for d in DIST_ALTERNATIVES.get(dist, set())
        }
        if not candidates & declared:
            report.warnings.append(
                f"line {line}: imports `{module}`, but requirements does not "
                f"list `{dist}` (or the pip name differs). Add it, and install it "
                f"in the app environment too."
            )


def other_decorators(
    func: ast.FunctionDef | ast.AsyncFunctionDef, report: Report
) -> None:
    """Warn about decorators other than @actuator."""
    extra = [d for d in func.decorator_list if not is_actuator_factory(d)]
    if extra:
        report.warnings.append(
            "the function has other decorators. Decorator lines are not "
            "uploaded, so they have no effect in method.py."
        )


def unguarded_calls(tree: ast.Module, names: set[str]) -> list[tuple[str, int]]:
    """Find module-level calls to registered functions with no __main__ guard."""
    found = []
    for node in tree.body:
        call = None
        if isinstance(node, ast.Expr):
            call = node.value
        elif isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
            call = node.value
        if (
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Name)
            and call.func.id in names
        ):
            found.append((call.func.id, node.lineno))
    return found


def check_file(path: Path) -> list[Report]:
    """Check every actuator in one file."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    module_kinds = module_level_bindings(tree)
    functions = {
        n.name: n
        for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    targets: list[tuple[ast.FunctionDef | ast.AsyncFunctionDef, ast.Call]] = []
    registrars: set[str] = set()
    for func in functions.values():
        for dec in func.decorator_list:
            if is_actuator_factory(dec):
                targets.append((func, dec))
                registrars.add(func.name)
    # publish = actuator(...)(func)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and is_actuator_factory(node.func)
            and node.args
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id in functions
        ):
            targets.append((functions[node.args[0].id], node.func))

    for node in tree.body:
        if isinstance(node, ast.Assign) and is_actuator_factory(
            getattr(node.value, "func", None)
        ):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    registrars.add(target.id)

    reports = []
    for func, call in targets:
        report = Report(label=f"{path}:{func.lineno} {func.name}()")
        requirements = check_decorator_args(call, report)
        check_signature(func, report)
        # Names local to this function never shadow module names in method.py.
        check_free_names(func, module_kinds, report)
        if requirements is not None:
            check_requirements(func, requirements, report)
        other_decorators(func, report)
        reports.append(report)

    for name, line in unguarded_calls(tree, registrars):
        report = Report(label=f"{path}:{line} {name}()")
        report.warnings.append(
            f"`{name}()` runs at module level, so the actuator is published "
            f"each time the module is imported. Put the call under "
            f"`if __name__ == \"__main__\":`."
        )
        reports.append(report)

    if not targets:
        empty = Report(label=str(path))
        empty.notes.append("no @actuator functions found.")
        reports.append(empty)
    return reports


def main() -> int:
    """Run the checks and print a report."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args()

    error_count = 0
    for path in args.files:
        try:
            reports = check_file(path)
        except (OSError, SyntaxError) as exc:
            print(f"{path}: cannot check: {exc}")
            error_count += 1
            continue
        for report in reports:
            status = "FAIL" if report.errors else "warn" if report.warnings else "ok"
            print(f"[{status}] {report.label}")
            for msg in report.errors:
                print(f"    error:   {msg}")
            for msg in report.warnings:
                print(f"    warning: {msg}")
            for msg in report.notes:
                print(f"    note:    {msg}")
            error_count += len(report.errors)
    return 1 if error_count else 0


if __name__ == "__main__":
    sys.exit(main())
