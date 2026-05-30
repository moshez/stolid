# Helper functions for AST inspection.

from __future__ import annotations

import ast
import os
from typing import AbstractSet, Iterable, Iterator, TypeGuard

FUNCTION_DEF_NODES = (ast.FunctionDef, ast.AsyncFunctionDef)
FunctionType = ast.FunctionDef | ast.AsyncFunctionDef
NAMED_DEF_NODES = FUNCTION_DEF_NODES + (ast.ClassDef,)
TUPLE_LIST_NODES = (ast.Tuple, ast.List)
COLLECTION_NODES = TUPLE_LIST_NODES + (ast.Set,)
LAMBDA_FUNCTION_NODES = FUNCTION_DEF_NODES + (ast.Lambda,)
SCOPE_NODES = NAMED_DEF_NODES + (ast.Lambda,)
COMPREHENSION_NODES = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
FOR_LOOP_NODES = (ast.For, ast.AsyncFor)


def iter_name_targets(target: ast.expr) -> Iterator[ast.Name]:
    """Yield every ``ast.Name`` reachable from assignment ``target``.

    Recurses through tuple/list targets and ``Starred`` wrappers; other
    expression shapes (attribute, subscript) yield nothing.

    Args:
        target: The assignment target expression to walk.

    Yields:
        Each ``ast.Name`` bound by ``target``.
    """
    if isinstance(target, ast.Name):
        yield target
    elif isinstance(target, TUPLE_LIST_NODES):
        for elt in target.elts:
            yield from iter_name_targets(elt)
    elif isinstance(target, ast.Starred):
        yield from iter_name_targets(target.value)


def iter_args(arguments: ast.arguments) -> Iterator[ast.arg]:
    """Yield every ``ast.arg`` in ``arguments``.

    Visits ``posonlyargs``, ``args``, ``kwonlyargs``, then ``vararg`` and
    ``kwarg`` if present.

    Args:
        arguments: The ``ast.arguments`` node to enumerate.

    Yields:
        Each ``ast.arg`` declared in ``arguments``.
    """
    yield from arguments.posonlyargs
    yield from arguments.args
    yield from arguments.kwonlyargs
    if arguments.vararg is not None:
        yield arguments.vararg
    if arguments.kwarg is not None:
        yield arguments.kwarg


def is_name_id(node: ast.AST, name: str) -> TypeGuard[ast.Name]:
    """Return True iff ``node`` is ``ast.Name`` with id ``name``.

    Args:
        node: The AST node to test.
        name: The identifier to match against ``node.id``.

    Returns:
        True when ``node`` is an ``ast.Name`` whose id equals ``name``.
    """
    return isinstance(node, ast.Name) and node.id == name


def is_name_among(node: ast.AST, names: Iterable[str]) -> bool:
    """Return True iff ``node`` is ``ast.Name`` whose id is in ``names``.

    Args:
        node: The AST node to test.
        names: The identifiers to match against ``node.id``.

    Returns:
        True when ``node`` is an ``ast.Name`` whose id is in ``names``.
    """
    return isinstance(node, ast.Name) and node.id in names


def is_attribute_attr(node: ast.AST, attr: str) -> bool:
    """Return True iff ``node`` is ``ast.Attribute`` with ``.attr`` == ``attr``.

    Args:
        node: The AST node to test.
        attr: The attribute name to match against ``node.attr``.

    Returns:
        True when ``node`` is an ``ast.Attribute`` whose attr equals ``attr``.
    """
    return isinstance(node, ast.Attribute) and node.attr == attr


def is_attribute_in(node: ast.AST, attrs: Iterable[str]) -> bool:
    """Return True iff ``node`` is ``ast.Attribute`` whose attr is in ``attrs``.

    Args:
        node: The AST node to test.
        attrs: The attribute names to match against ``node.attr``.

    Returns:
        True when ``node`` is an ``ast.Attribute`` whose attr is in ``attrs``.
    """
    return isinstance(node, ast.Attribute) and node.attr in attrs


def safe_parse(source: str, filename: str) -> ast.Module | None:
    """Return ``ast.parse(source, filename=filename)`` or ``None`` on ``SyntaxError``.

    Cross-file scanners use this to skip un-parseable files rather than abort
    the whole scan.

    Args:
        source: The Python source text to parse.
        filename: The filename associated with ``source`` for diagnostics.

    Returns:
        The parsed module, or ``None`` if ``source`` is not valid Python.
    """
    try:
        return ast.parse(source, filename=filename)
    except SyntaxError:
        return None


def is_type_checking_test(node: ast.expr) -> bool:
    """Return True iff ``node`` is the test of an ``if TYPE_CHECKING:`` guard.

    Matches ``TYPE_CHECKING``, ``typing.TYPE_CHECKING``, ``t.TYPE_CHECKING``
    (and any other ``foo.TYPE_CHECKING`` alias) syntactically.

    Args:
        node: The ``if`` test expression to inspect.

    Returns:
        True when ``node`` names ``TYPE_CHECKING`` directly or as an attribute.
    """
    if isinstance(node, ast.Name):
        return node.id == "TYPE_CHECKING"
    if isinstance(node, ast.Attribute):
        return node.attr == "TYPE_CHECKING"
    return False


def iter_runtime_nodes(node: ast.AST) -> Iterator[ast.AST]:
    """Yield descendants of ``node``, skipping bodies of ``if TYPE_CHECKING:``.

    The ``else:`` branch of a ``TYPE_CHECKING`` guard still executes at
    runtime and is visited.

    Args:
        node: The AST node whose runtime descendants to walk.

    Yields:
        ``node`` and each descendant reachable at runtime.
    """
    if isinstance(node, ast.If) and is_type_checking_test(node.test):
        for stmt in node.orelse:
            yield from iter_runtime_nodes(stmt)
        return
    yield node
    for child in ast.iter_child_nodes(node):
        yield from iter_runtime_nodes(child)


def get_base_name(node: ast.expr) -> str | None:
    """Return the base-class name expressed by ``node``, or ``None`` if unknown.

    Args:
        node: The base-class expression to resolve.

    Returns:
        The simple name of the base class, or ``None`` if it cannot be derived.
    """
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Subscript):
        return get_base_name(node.value)
    return None


def is_dataclass_decorator(node: ast.expr) -> bool:
    """Return True iff ``node`` is a ``@dataclass`` or ``@dataclasses.dataclass``.

    Args:
        node: The decorator expression to inspect.

    Returns:
        True when ``node`` names the ``dataclass`` decorator, called or bare.
    """
    if is_name_id(node, "dataclass"):
        return True
    if is_attribute_attr(node, "dataclass"):
        return True
    if isinstance(node, ast.Call):
        return is_dataclass_decorator(node.func)
    return False


def has_dataclass_decorator(node: ast.ClassDef) -> bool:
    """Return True iff ``node`` carries a ``@dataclass`` decorator.

    Args:
        node: The class definition to inspect.

    Returns:
        True when any decorator on ``node`` is a ``dataclass`` decorator.
    """
    return any(is_dataclass_decorator(d) for d in node.decorator_list)


def is_dunder_name(name: str) -> bool:
    """Return True iff ``name`` is a dunder identifier (``__xxx__``).

    Args:
        name: The identifier to test.

    Returns:
        True when ``name`` starts and ends with a double underscore.
    """
    return name.startswith("__") and name.endswith("__")


def module_name_from_filename(filename: str) -> str | None:
    """Return the module basename of ``filename`` (no ``.py``), or ``None``.

    Returns ``None`` if ``filename`` is empty or does not end in ``.py``.
    Does not filter dunder modules; callers that care apply that check.

    Args:
        filename: The path whose module basename to extract.

    Returns:
        The basename without its ``.py`` suffix, or ``None`` if inapplicable.
    """
    if not filename:
        return None
    base = os.path.basename(filename)
    if not base.endswith(".py"):
        return None
    return base[:-3]


def _add_matching_aliases(
    aliases: list[ast.alias], wanted: tuple[str, ...], target: set[str]
) -> None:
    for alias in aliases:
        if alias.name in wanted:
            target.add(alias.asname or alias.name)


_PATCH_NAMES_WANTED = ("patch", "patch.object")
_ABSTRACT_WANTED = ("abstractmethod",)
_CAST_WANTED = ("cast",)


def collect_imports(
    tree: ast.AST,
) -> tuple[AbstractSet[str], AbstractSet[str], AbstractSet[str]]:
    """Return names bound in ``tree`` that alias patch, abstractmethod, and cast.

    Args:
        tree: The module AST to scan for the relevant imports.

    Returns:
        The patch, abstractmethod, and cast name sets, in that order.
    """
    patch_names: set[str] = set()
    abstractmethod_names: set[str] = {"abstractmethod"}
    cast_names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module in ("unittest.mock", "mock"):  # noqa: SLD304
            _add_matching_aliases(node.names, _PATCH_NAMES_WANTED, patch_names)
        if node.module == "abc":  # noqa: SLD304
            _add_matching_aliases(node.names, _ABSTRACT_WANTED, abstractmethod_names)
        if node.module == "typing":  # noqa: SLD304
            _add_matching_aliases(node.names, _CAST_WANTED, cast_names)
    return patch_names, abstractmethod_names, cast_names
