from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional, Callable, List, Tuple
import lang_ast as ast
from tokens import TokenType

class RuntimeError_(Exception): pass

# env + types

class Environment:
    def __init__(self, parent: Optional["Environment"]=None):
        self.parent = parent
        self.values: Dict[str, Any] = {}
        self.types: Dict[str, Optional[str]] = {}

    def define(self, name: str, value: Any, type_name: Optional[str]=None):
        self.values[name] = value
        self.types[name] = type_name

    def assign(self, name: str, value: Any):
        env = self._find(name)
        if env is None: raise RuntimeError_(f"Undefined variable '{name}'")
        tname = env.types.get(name)
        if tname and value is not None:
            value = cast_to(tname, value)
        env.values[name] = value

    def get(self, name: str) -> Any:
        env = self._find(name)
        if env is None: raise RuntimeError_(f"Undefined variable '{name}'")
        return env.values[name]

    def declared_type(self, name: str) -> Optional[str]:
        env = self._find(name)
        if env is None: raise RuntimeError_(f"Undefined variable '{name}'")
        return env.types.get(name)

    def _find(self, name: str) -> Optional["Environment"]:
        env: Optional[Environment] = self
        while env is not None:
            if name in env.values: return env
            env = env.parent
        return None

# functions

@dataclass
class BuiltinFunction:
    name: str
    arity: Optional[int]
    impl: Callable[..., Any]
    def __call__(self, *args, **kwargs): return self.impl(*args, **kwargs)

@dataclass
class UserFunction:
    name: str
    params: list[ast.Param]
    body: ast.Block
    closure: Environment
    def __call__(self, *args, **kwargs):
        # note: defaults evaluated in local env
        if len(args) > len(self.params):
            raise RuntimeError_(f"Function '{self.name}' expected at most {len(self.params)} args, got {len(args)}")
        local = Environment(self.closure)
        pos_i = 0
        for p in self.params:
            has_kw = p.name in kwargs
            if pos_i < len(args) and not has_kw:
                val = args[pos_i]; pos_i += 1
            elif has_kw:
                val = kwargs.pop(p.name)
            elif p.default is not None:
                val = Interpreter.eval_expr_static(p.default, local)
            else:
                raise RuntimeError_(f"Function '{self.name}' missing argument '{p.name}'")
            if val is not None:
                try:
                    val = cast_to(p.type_name, val)
                except RuntimeError_ as e:
                    raise
            local.define(p.name, val, p.type_name)
        if kwargs:
            unknown = ", ".join(kwargs.keys())
            raise RuntimeError_(f"Function '{self.name}' got unknown keyword arguments: {unknown}")
        try:
            return Interpreter.eval_block(self.body, local)
        except ReturnSignal as rs:
            return rs.value
        # return Interpreter.eval_block(self.body, local)  # (alt)

class ReturnSignal(Exception):
    def __init__(self, value): self.value = value

# casting

PRIMITIVE_CASTERS = {
    "byte":  lambda v: int(v) & 0xFF,
    "short": int,
    "int":   int,
    "long":  int,
    "bool":  bool,
    "float": float,
    "double": float,
    "char":  lambda v: str(v)[0] if v is not None else None,
    "string": lambda v: str(v) if v is not None else None,
}

def cast_to(type_name: str, value: Any) -> Any:
    caster = PRIMITIVE_CASTERS.get(type_name)
    if caster is None: raise RuntimeError_(f"Unknown type '{type_name}'")
    try:
        return caster(value)
    except Exception as e:
        raise RuntimeError_(f"Cannot cast {value!r} to {type_name}: {e}")

# interpreter

class Interpreter:
    def __init__(self, env: Optional[Environment]=None):
        self.globals = env or Environment()

    # program entry (2-pass hoist)
    def run(self, statements: list[ast.Stmt]):
        for s in statements:
            if isinstance(s, ast.FnDecl):
                fn = UserFunction(s.name, s.params, s.body, self.globals)
                self.globals.define(s.name, fn, None)

        for s in statements:
            if isinstance(s, ast.FnDecl): continue
            self.execute(s, self.globals)

    @staticmethod
    def eval_block(block: ast.Block, env: Environment):
        inter = Interpreter(env)
        for s in block.statements:
            inter.execute(s, env)
        return None

    @staticmethod
    def eval_expr_static(expr: ast.Expr, env: Environment):
        inter = Interpreter(env)
        return inter.evaluate(expr, env)

    # statements
    def execute(self, stmt: ast.Stmt, env: Environment):
        if isinstance(stmt, ast.VarDecl):
            for name, init in zip(stmt.names, stmt.initializers):
                value = self.evaluate(init, env) if init is not None else None
                if value is not None:
                    value = cast_to(stmt.type_name, value)
                env.define(name, value, stmt.type_name)
            return

        if isinstance(stmt, ast.ExprStmt):
            self.evaluate(stmt.expr, env); return

        if isinstance(stmt, ast.Block):
            new_env = Environment(env)
            for s in stmt.statements:
                self.execute(s, new_env)
            return

        if isinstance(stmt, ast.IfStmt):
            # little scope: setup runs here
            branch_env = Environment(env)
            for s in stmt.setup:
                self.execute(s, branch_env)
            cond = self.is_truthy(self.evaluate(stmt.condition, branch_env))
            if cond:
                self.execute(stmt.then_branch, branch_env)
            elif stmt.else_branch:
                self.execute(stmt.else_branch, env)
            return

        if isinstance(stmt, ast.WhileStmt):
            loop_env = Environment(env)
            if stmt.init: self.execute(stmt.init, loop_env)
            ran = False
            while self.is_truthy(self.evaluate(stmt.condition, loop_env)):
                ran = True
                self.execute(stmt.body, loop_env)
                if stmt.update: self.evaluate(stmt.update, loop_env)
            if not ran and stmt.else_branch:
                self.execute(stmt.else_branch, env)
            return

        if isinstance(stmt, ast.ForStmt):
            loop_env = Environment(env)
            if stmt.init: self.execute(stmt.init, loop_env)
            while self.is_truthy(self.evaluate(stmt.condition, loop_env)):
                self.execute(stmt.body, loop_env)
                if stmt.update: self.evaluate(stmt.update, loop_env)
            return

        if isinstance(stmt, ast.ReturnStmt):
            val = self.evaluate(stmt.value, env) if stmt.value is not None else None
            raise ReturnSignal(val)

        if isinstance(stmt, ast.FnDecl):
            fn = UserFunction(stmt.name, stmt.params, stmt.body, env)
            env.define(stmt.name, fn, None); return

        raise RuntimeError_(f"Unknown statement: {stmt}")

    # expressions
    def evaluate(self, expr: Optional[ast.Expr], env: Environment):
        if expr is None: return None

        if isinstance(expr, ast.Literal): return expr.value

        if isinstance(expr, ast.Var): return env.get(expr.name)

        if isinstance(expr, ast.Assign):
            value = self.evaluate(expr.value, env)
            env.assign(expr.name, value); return value

        if isinstance(expr, ast.AugAssign):
            cur = env.get(expr.name)
            val = self.evaluate(expr.value, env)
            op = expr.op
            if cur is None or val is None:
                raise RuntimeError_(f"Cannot use augmented assignment on null value for '{expr.name}'")
            if op == TokenType.PLUS_EQUAL:
                if isinstance(cur, str) or isinstance(val, str):
                    res = str(cur) + str(val)
                else:
                    res = cur + val
            elif op == TokenType.MINUS_EQUAL:   res = cur - val
            elif op == TokenType.STAR_EQUAL:    res = cur * val
            elif op == TokenType.SLASH_EQUAL:   res = cur / val
            elif op == TokenType.PERCENT_EQUAL: res = cur % val
            else:
                raise RuntimeError_(f"Unknown augmented operator {op}")
            env.assign(expr.name, res); return res
            # res = cur + val if op == TokenType.PLUS_EQUAL else res  # (alt concat sketch)

        if isinstance(expr, ast.Update):
            cur = env.get(expr.name)
            if cur is None:
                raise RuntimeError_(f"Cannot apply ++/-- to null '{expr.name}'")
            if expr.op == TokenType.PLUS_PLUS: new = cur + 1
            elif expr.op == TokenType.MINUS_MINUS: new = cur - 1
            else: raise RuntimeError_(f"Unknown update operator {expr.op}")
            env.assign(expr.name, new)
            return new if expr.prefix else cur

        if isinstance(expr, ast.Unary):
            right = self.evaluate(expr.right, env)
            if expr.op in (TokenType.MINUS,): return -self._num(right)
            if expr.op in (TokenType.BANG, TokenType.NOT): return not self.is_truthy(right)
            raise RuntimeError_(f"Unknown unary operator {expr.op}")

        if isinstance(expr, ast.Binary):
            left = self.evaluate(expr.left, env)
            right = self.evaluate(expr.right, env)
            t = expr.op
            if t == TokenType.PLUS:
                if isinstance(left, str) or isinstance(right, str):
                    return str(left) + str(right)
                return left + right
            if t == TokenType.MINUS: return left - right
            if t == TokenType.STAR: return left * right
            if t == TokenType.SLASH: return left / right
            if t == TokenType.PERCENT: return left % right
            if t == TokenType.STAR_STAR: return left ** right
            if t == TokenType.EQUAL_EQUAL: return left == right
            if t == TokenType.BANG_EQUAL: return left != right
            if t == TokenType.GREATER: return left > right
            if t == TokenType.GREATER_EQUAL: return left >= right
            if t == TokenType.LESS: return left < right
            if t == TokenType.LESS_EQUAL: return left <= right
            raise RuntimeError_(f"Unknown binary operator {t}")
            # if t == TokenType.PLUS: return left + right  # (fallback idea, commented)

        if isinstance(expr, ast.Logical):
            if expr.op in (TokenType.OR, TokenType.OR_OR):
                left = self.evaluate(expr.left, env)
                if self.is_truthy(left): return True
                return self.is_truthy(self.evaluate(expr.right, env))
            else:
                left = self.evaluate(expr.left, env)
                if not self.is_truthy(left): return False
                return self.is_truthy(self.evaluate(expr.right, env))

        if isinstance(expr, ast.Cast):
            v = self.evaluate(expr.expr, env)
            if v is None: return None
            return cast_to(expr.type_name, v)

        if isinstance(expr, ast.Call):
            callee = self.evaluate(expr.callee, env)
            pos: List[Any] = []; kw: Dict[str, Any] = {}
            for a in expr.args:
                if a.name is None:
                    pos.append(self.evaluate(a.value, env))
                else:
                    kw[a.name] = self.evaluate(a.value, env)
            if not callable(callee):
                raise RuntimeError_(f"Attempted to call non-function: {callee!r}")
            return callee(*pos, **kw)

        raise RuntimeError_(f"Unknown expression: {expr}")

    # helpers
    def is_truthy(self, v: Any) -> bool:
        return bool(v)

    def _num(self, v: Any) -> float | int:
        if isinstance(v, (int, float)): return v
        raise RuntimeError_(f"Expected a number, got {type(v).__name__}")
