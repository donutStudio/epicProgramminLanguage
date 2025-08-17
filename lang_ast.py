from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional

# statements

@dataclass
class Stmt: ...

@dataclass
class VarDecl(Stmt):
    type_name: str
    names: list[str]
    initializers: list[Optional["Expr"]]

@dataclass
class ExprStmt(Stmt):
    expr: "Expr"

@dataclass
class Block(Stmt):
    statements: list[Stmt]

# if / else-if / else
@dataclass
class IfStmt(Stmt):
    setup: list[Stmt]
    condition: "Expr"
    then_branch: Block
    else_branch: Optional["Stmt"]   # IfStmt or Block

# while / while with (init;cond;update;)
@dataclass
class WhileStmt(Stmt):
    init: Optional[Stmt]
    condition: "Expr"
    update: Optional["Expr"]
    body: Block
    else_branch: Optional["Stmt"]

@dataclass
class ForStmt(Stmt):
    init: Optional[Stmt]
    condition: Optional["Expr"]
    update: Optional["Expr"]
    body: Block

@dataclass
class ReturnStmt(Stmt):
    value: Optional["Expr"]

@dataclass
class Param:
    type_name: str
    name: str
    default: Optional["Expr"]

@dataclass
class FnDecl(Stmt):
    name: str
    params: list[Param]
    body: Block

# expressions

@dataclass
class Expr: ...

@dataclass
class Literal(Expr):
    value: object

@dataclass
class Var(Expr):
    name: str

@dataclass
class Assign(Expr):
    name: str
    value: Expr

@dataclass
class AugAssign(Expr):
    name: str
    op: str
    value: Expr

@dataclass
class Update(Expr):
    name: str
    op: str
    prefix: bool

@dataclass
class Unary(Expr):
    op: str
    right: Expr

@dataclass
class Binary(Expr):
    left: Expr
    op: str
    right: Expr

@dataclass
class Logical(Expr):
    left: Expr
    op: str
    right: Expr

@dataclass
class Cast(Expr):
    type_name: str
    expr: Expr

@dataclass
class CallArg:
    name: Optional[str]
    value: Expr

@dataclass
class Call(Expr):
    callee: Expr
    args: list[CallArg]
