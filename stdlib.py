from __future__ import annotations
from typing import Any
from runtime import BuiltinFunction, Environment, RuntimeError_

def install_builtins(env: Environment) -> None:
    # minimal notes: keyword validation kept strict to surface misuse early
    def _stringify(v: Any) -> str:
        return "null" if v is None else str(v)

    def _print(*args: Any, **kwargs: Any) -> None:
        allowed = {"message", "sep", "end"}
        unknown = set(kwargs) - allowed
        if unknown:
            keys = ", ".join(sorted(unknown))
            raise RuntimeError_(f"print() got unexpected keyword(s): {keys}")
        sep = kwargs.get("sep", " ")
        end = kwargs.get("end", "\n")
        if "message" in kwargs:
            if args:
                raise RuntimeError_("print() cannot take both positional args and 'message='")
            text = _stringify(kwargs["message"])
            print(text, end=end); return None
        text = sep.join(_stringify(a) for a in args)
        print(text, end=end); return None

    env.define("print", BuiltinFunction("print", None, _print), None)

    def _len(x: Any, **kwargs: Any) -> int:
        if kwargs:
            keys = ", ".join(sorted(kwargs.keys()))
            raise RuntimeError_(f"len() got unexpected keyword(s): {keys}")
        try:
            return len(x)  # type: ignore[arg-type]
        except Exception:
            raise RuntimeError_(f"len() not supported for {type(x).__name__}")

    env.define("len", BuiltinFunction("len", 1, _len), None)

    def _typeof(x: Any, **kwargs: Any) -> str:
        if kwargs:
            keys = ", ".join(sorted(kwargs.keys()))
            raise RuntimeError_(f"typeof() got unexpected keyword(s): {keys}")
        if x is None: return "null"
        if isinstance(x, bool): return "bool"
        if isinstance(x, int):  return "int"
        if isinstance(x, float): return "float"
        if isinstance(x, str):  return "string"
        return type(x).__name__

    env.define("typeof", BuiltinFunction("typeof", 1, _typeof), None)

    def _to_string(x: Any, **kwargs: Any) -> str:
        if kwargs:
            keys = ", ".join(sorted(kwargs.keys()))
            raise RuntimeError_(f"to_string() got unexpected keyword(s): {keys}")
        return _stringify(x)

    env.define("to_string", BuiltinFunction("to_string", 1, _to_string), None)
