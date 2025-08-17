# parser.py
from __future__ import annotations
from typing import List, Optional, Tuple
from tokens import Token, TokenType, PRIMITIVE_TYPES
from lexer import Lexer, LexerError
import lang_ast as ast

class ParseError(Exception): pass

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.current = 0
        self.errors: List[str] = []

    @staticmethod
    def from_source(source: str) -> "Parser":
        lx = Lexer(source)
        toks = lx.scan_tokens()
        return Parser(toks)

    # driver
    def parse(self) -> List[ast.Stmt]:
        statements: List[ast.Stmt] = []
        while not self.check(TokenType.EOF):
            self._skip_newlines()
            if self.check(TokenType.EOF): break
            try:
                statements.append(self.declaration_or_statement())
            except ParseError as e:
                self.errors.append(str(e))
                self.synchronize()
        return statements

    # util
    def _skip_newlines(self):
        while not self.is_at_end() and self.peek_raw().type == TokenType.NEWLINE:
            self.current += 1

    def match(self, *types) -> bool:
        self._skip_newlines()
        for t in types:
            if self.check(t):
                self.advance(); return True
        return False

    def check(self, type_) -> bool:
        self._skip_newlines()
        if self.is_at_end(): return type_ == TokenType.EOF
        return self.peek().type == type_

    def is_at_end(self) -> bool:
        return self.peek_raw().type == TokenType.EOF

    def peek_raw(self) -> Token: return self.tokens[self.current]

    def peek(self) -> Token:
        self._skip_newlines()
        return self.tokens[self.current]

    def previous(self) -> Token: return self.tokens[self.current - 1]

    def advance(self) -> Token:
        if not self.is_at_end(): self.current += 1
        return self.previous()

    def consume(self, type_, message: str) -> Token:
        if self.check(type_): return self.advance()
        raise ParseError(f"{message} at line {self.peek().line}")

    def synchronize(self):
        while not self.check(TokenType.EOF):
            if self.match(TokenType.SEMICOLON): return
            if self.check(TokenType.RIGHT_BRACE): return
            self.current += 1

    # top-level
    def declaration_or_statement(self) -> ast.Stmt:
        if self.check(TokenType.TYPE):
            return self.var_declaration(strict_terminator=True)
        if self.match(TokenType.FUNCTION, TokenType.FN):
            return self.fn_declaration()
        if self.match(TokenType.IF): return self.if_statement()
        if self.match(TokenType.WHILE): return self.while_statement()
        if self.match(TokenType.FOR): return self.for_statement()
        if self.match(TokenType.RETURN): return self.return_statement()
        return self.expr_statement()

    # TYPE name ( "=" expr )? ( "," name ( "=" expr )? )* ";"
    def var_declaration(self, strict_terminator: bool) -> ast.VarDecl:
        type_tok = self.consume(TokenType.TYPE, "Expected a type at start of declaration")
        names: list[str] = []; inits: list[Optional[ast.Expr]] = []
        names.append(self.consume(TokenType.IDENTIFIER, "Expected a variable name").lexeme)
        init = None
        if self.match(TokenType.EQUAL): init = self.expression()
        inits.append(init)
        while self.match(TokenType.COMMA):
            names.append(self.consume(TokenType.IDENTIFIER, "Expected a variable name").lexeme)
            init2 = None
            if self.match(TokenType.EQUAL): init2 = self.expression()
            inits.append(init2)
        if strict_terminator: self.consume(TokenType.SEMICOLON, "Expected ';' to terminate declaration")
        return ast.VarDecl(type_tok.literal, names, inits)

    # function name "(" ( param (";" param)* ";"? )? ")" block
    # param -> TYPE IDENT ( "=" expression )?
    def fn_declaration(self) -> ast.FnDecl:
        name = self.consume(TokenType.IDENTIFIER, "Expected function name").lexeme
        self.consume(TokenType.LEFT_PAREN, "Expected '(' after function name")
        params: list[ast.Param] = []
        if not self.check(TokenType.RIGHT_PAREN):
            params.append(self.param())
            while self.match(TokenType.SEMICOLON):
                if self.check(TokenType.RIGHT_PAREN): break
                params.append(self.param())
        self.consume(TokenType.RIGHT_PAREN, "Expected ')' after parameters")
        body = self.block()
        return ast.FnDecl(name, params, body)

    def param(self) -> ast.Param:
        t = self.consume(TokenType.TYPE, "Expected parameter type").literal
        name = self.consume(TokenType.IDENTIFIER, "Expected parameter name").lexeme
        default = None
        if self.match(TokenType.EQUAL): default = self.expression()
        return ast.Param(t, name, default)

    def block(self) -> ast.Block:
        self.consume(TokenType.LEFT_BRACE, "Expected '{' to start block")
        stmts: list[ast.Stmt] = []
        while not self.check(TokenType.RIGHT_BRACE) and not self.check(TokenType.EOF):
            stmts.append(self.declaration_or_statement())
        self.consume(TokenType.RIGHT_BRACE, "Expected '}' after block")
        return ast.Block(stmts)

    # statements
    def if_statement(self) -> ast.IfStmt:
        # note: tiny control group feature
        setup, cond = self.condition_group("if")
        then_b = self.block()
        else_branch: Optional[ast.Stmt] = None
        if self.match(TokenType.ELSE):
            if self.match(TokenType.IF):
                else_branch = self.if_statement()
            else:
                else_branch = self.block()
        return ast.IfStmt(setup, cond, then_b, else_branch)

    def while_statement(self) -> ast.WhileStmt:
        init, cond, update = self.while_group()
        body = self.block()
        else_branch: Optional[ast.Stmt] = None
        if self.match(TokenType.ELSE):
            if self.match(TokenType.WHILE):
                else_branch = self.while_statement()
            else:
                else_branch = self.block()
        return ast.WhileStmt(init, cond, update, body, else_branch)

    def for_statement(self) -> ast.ForStmt:
        self.consume(TokenType.LEFT_PAREN, "Expected '(' after 'for'")
        init_stmt = self.for_init_segment()
        self.consume(TokenType.SEMICOLON, "Expected ';' after for-init")
        cond = self.expression()
        self.consume(TokenType.SEMICOLON, "Expected ';' after for-condition")
        upd = self.expression()
        if self.match(TokenType.SEMICOLON): pass
        self.consume(TokenType.RIGHT_PAREN, "Expected ')' after for-clause")
        body = self.block()
        return ast.ForStmt(init_stmt, cond, upd, body)

    def for_init_segment(self) -> Optional[ast.Stmt]:
        if self.check(TokenType.TYPE):
            return self.var_declaration(strict_terminator=False)
        else:
            expr = self.expression()
            return ast.ExprStmt(expr)

    def return_statement(self) -> ast.ReturnStmt:
        if self.check(TokenType.SEMICOLON):
            self.advance(); return ast.ReturnStmt(None)
        value = None
        if not self.check(TokenType.SEMICOLON):
            value = self.expression()
        self.consume(TokenType.SEMICOLON, "Expected ';' after return")
        return ast.ReturnStmt(value)

    def expr_statement(self) -> ast.ExprStmt:
        expr = self.expression()
        self.consume(TokenType.SEMICOLON, "Expected ';' after expression")
        return ast.ExprStmt(expr)

    # conditions
    def condition_group(self, who: str) -> Tuple[list[ast.Stmt], ast.Expr]:
        if self.match(TokenType.LEFT_PAREN):
            setup, cond = self.clause_list_until(TokenType.RIGHT_PAREN, require_last_expr=True, context=who)
            self.consume(TokenType.RIGHT_PAREN, f"Expected ')' to close {who} condition")
            return setup, cond
        elif self.match(TokenType.LEFT_BRACE):
            setup, cond = self.clause_list_until(TokenType.RIGHT_BRACE, require_last_expr=True, context=who)
            self.consume(TokenType.RIGHT_BRACE, f"Expected '}}' to close {who} condition")
            return setup, cond
        else:
            raise ParseError(f"Expected '(' or '{{' after {who}")

    def while_group(self) -> Tuple[Optional[ast.Stmt], ast.Expr, Optional[ast.Expr]]:
        # (subtle) supports both 1-clause and 3-clause forms
        self.consume(TokenType.LEFT_PAREN, "Expected '(' after 'while'")
        clauses: list = []
        if self.check(TokenType.RIGHT_PAREN): raise ParseError("Empty while condition is not allowed")
        clauses.append(self._clause_item())
        self.consume(TokenType.SEMICOLON, "Expected ';' after while clause")
        if self.check(TokenType.RIGHT_PAREN):
            raise ParseError("While condition missing expression before ')'")
        if not self.check(TokenType.RIGHT_PAREN):
            clause2 = self._clause_item()
            if self.match(TokenType.SEMICOLON):
                # 3-clause
                init_stmt = self._as_setup_stmt(clauses[0])
                cond_expr = self._as_expr(clause2, "while condition must be an expression")
                update_expr = self._clause_expr("while update must be an expression")
                if self.match(TokenType.SEMICOLON): pass
                self.consume(TokenType.RIGHT_PAREN, "Expected ')' after while clauses")
                return init_stmt, cond_expr, update_expr
            else:
                # 1-clause
                cond_expr = self._as_expr(clause2, "while condition must be an expression")
                self.consume(TokenType.RIGHT_PAREN, "Expected ')' after while condition")
                return None, cond_expr, None
        raise ParseError("Malformed while condition")
        # return None, self._as_expr(clauses[0], "while condition must be an expression"), None  # (alt idea)

    def clause_list_until(self, end_token: str, require_last_expr: bool, context: str) -> Tuple[list[ast.Stmt], ast.Expr]:
        setup_stmts: list[ast.Stmt] = []; items: list = []
        if self.check(end_token): raise ParseError(f"{context} condition cannot be empty")
        items.append(self._clause_item())
        self.consume(TokenType.SEMICOLON, f"Expected ';' separating {context} clauses")
        while not self.check(end_token):
            if self.check(end_token): break
            if self.check(TokenType.RIGHT_PAREN) or self.check(TokenType.RIGHT_BRACE): break
            items.append(self._clause_item())
            if not self.match(TokenType.SEMICOLON):
                raise ParseError(f"Expected ';' separating {context} clauses")
        last = items[-1]
        cond_expr = self._as_expr(last, f"{context} last clause must be an expression")
        for it in items[:-1]:
            setup_stmts.append(self._as_setup_stmt(it))
        return setup_stmts, cond_expr

    def _clause_item(self):
        if self.check(TokenType.TYPE):
            return self.var_declaration(strict_terminator=False)
        else:
            return self.expression()

    def _as_expr(self, item, msg: str) -> ast.Expr:
        if isinstance(item, ast.Expr): return item
        raise ParseError(msg)

    def _as_setup_stmt(self, item) -> ast.Stmt:
        if isinstance(item, ast.VarDecl): return item
        if isinstance(item, ast.Expr): return ast.ExprStmt(item)
        raise ParseError("Invalid clause in condition")

    def _clause_expr(self, msg: str) -> ast.Expr:
        expr = self.expression()
        return expr

    # expressions
    def expression(self) -> ast.Expr:
        return self.assignment()

    # IDENT ( "=" | "+=" | "-=" | "*=" | "/=" | "%=" ) assignment | logic_or
    def assignment(self) -> ast.Expr:
        expr = self.logic_or()
        if self.match(TokenType.EQUAL, TokenType.PLUS_EQUAL, TokenType.MINUS_EQUAL,
                      TokenType.STAR_EQUAL, TokenType.SLASH_EQUAL, TokenType.PERCENT_EQUAL):
            op = self.previous().type
            if isinstance(expr, ast.Var):
                value = self.assignment()
                if op == TokenType.EQUAL:
                    return ast.Assign(expr.name, value)
                else:
                    return ast.AugAssign(expr.name, op, value)
            # return ast.Assign(expr.name, value)  # shadow idea, keeping it commented
            raise ParseError("Invalid assignment target")
        return expr

    def logic_or(self) -> ast.Expr:
        expr = self.logic_and()
        while self.match(TokenType.OR, TokenType.OR_OR):
            op = self.previous().type
            right = self.logic_and()
            expr = ast.Logical(expr, op, right)
        return expr

    def logic_and(self) -> ast.Expr:
        expr = self.equality()
        while self.match(TokenType.AND, TokenType.AND_AND):
            op = self.previous().type
            right = self.equality()
            expr = ast.Logical(expr, op, right)
        return expr

    def equality(self) -> ast.Expr:
        expr = self.comparison()
        while self.match(TokenType.EQUAL_EQUAL, TokenType.BANG_EQUAL):
            op = self.previous().type
            right = self.comparison()
            expr = ast.Binary(expr, op, right)
        return expr

    def comparison(self) -> ast.Expr:
        expr = self.term()
        while self.match(TokenType.GREATER, TokenType.GREATER_EQUAL, TokenType.LESS, TokenType.LESS_EQUAL):
            op = self.previous().type
            right = self.term()
            expr = ast.Binary(expr, op, right)
        return expr

    def term(self) -> ast.Expr:
        expr = self.factor()
        while self.match(TokenType.MINUS, TokenType.PLUS):
            op = self.previous().type
            right = self.factor()
            expr = ast.Binary(expr, op, right)
        return expr

    def factor(self) -> ast.Expr:
        expr = self.power()
        while self.match(TokenType.SLASH, TokenType.STAR, TokenType.PERCENT):
            op = self.previous().type
            right = self.power()
            expr = ast.Binary(expr, op, right)
        return expr

    def power(self) -> ast.Expr:
        expr = self.unary()
        while self.match(TokenType.STAR_STAR):
            op = self.previous().type
            right = self.unary()
            expr = ast.Binary(expr, op, right)
        return expr

    def unary(self) -> ast.Expr:
        if self.match(TokenType.BANG, TokenType.MINUS, TokenType.NOT):
            op = self.previous().type
            right = self.unary()
            return ast.Unary(op, right)
        if self.match(TokenType.PLUS_PLUS, TokenType.MINUS_MINUS):
            op = self.previous().type
            target = self.primary()
            if not isinstance(target, ast.Var):
                raise ParseError("Prefix ++/-- must be applied to a variable")
            return ast.Update(target.name, op, True)
        return self.call()

    def call(self) -> ast.Expr:
        # note: handles postfix updates too
        expr = self.primary()
        while True:
            if self.match(TokenType.LEFT_PAREN):
                args = self.arguments()
                self.consume(TokenType.RIGHT_PAREN, "Expected ')' after arguments")
                expr = ast.Call(expr, args); continue
            if self.match(TokenType.PLUS_PLUS, TokenType.MINUS_MINUS):
                if not isinstance(expr, ast.Var):
                    raise ParseError("Postfix ++/-- must be applied to a variable")
                op = self.previous().type
                expr = ast.Update(expr.name, op, False); continue
            break
        return expr

    # "(" ... already consumed
    # args -> ( arg (";" arg)* ";"? )?
    def arguments(self) -> list[ast.CallArg]:
        args: list[ast.CallArg] = []
        if self.check(TokenType.RIGHT_PAREN): return args
        args.append(self.argument())
        while self.match(TokenType.SEMICOLON):
            if self.check(TokenType.RIGHT_PAREN): break
            args.append(self.argument())
        return args

    def argument(self) -> ast.CallArg:
        if self.check(TokenType.IDENTIFIER):
            t = self.peek()
            save = self.current
            self.advance()
            is_kw = self.match(TokenType.EQUAL)
            self.current = save
            if is_kw:
                name = self.consume(TokenType.IDENTIFIER, "Expected argument name").lexeme
                self.consume(TokenType.EQUAL, "Expected '=' in keyword argument")
                value = self.expression()
                return ast.CallArg(name, value)
        value = self.expression()
        return ast.CallArg(None, value)

    def primary(self) -> ast.Expr:
        if self.match(TokenType.NULL):   return ast.Literal(None)
        if self.match(TokenType.CHAR):   return ast.Literal(self.previous().literal)
        if self.match(TokenType.INT):    return ast.Literal(self.previous().literal)
        if self.match(TokenType.FLOAT):  return ast.Literal(self.previous().literal)
        if self.match(TokenType.STRING): return ast.Literal(self.previous().literal)
        if self.match(TokenType.BOOL):   return ast.Literal(self.previous().literal)
        if self.match(TokenType.LEFT_PAREN):
            expr = self.expression()
            self.consume(TokenType.RIGHT_PAREN, "Expected ')' after expression")
            return expr
        if self.check(TokenType.TYPE):
            t = self.advance().literal
            right = self.unary()
            return ast.Cast(t, right)
        if self.match(TokenType.IDENTIFIER):
            return ast.Var(self.previous().lexeme)
        raise ParseError(f"Expected expression at line {self.peek().line}")
