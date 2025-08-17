from __future__ import annotations
from typing import List
from tokens import Token, TokenType, KEYWORDS, PRIMITIVE_TYPES

class LexerError(Exception):
    pass

class Lexer:
    def __init__(self, source: str):
        self.source = source.replace("\r\n", "\n").replace("\r", "\n")
        self.start = 0
        self.current = 0
        self.line = 1
        self.col = 1
        self.tokens: List[Token] = []

    def scan_tokens(self) -> List[Token]:
        while not self.is_at_end():
            self.start = self.current
            self.scan_token()
        self.tokens.append(Token(TokenType.EOF, "", None, self.line, self.col))
        return self.tokens

    # basics
    def is_at_end(self) -> bool:
        return self.current >= len(self.source)

    def advance(self) -> str:
        if self.is_at_end(): return "\0"
        ch = self.source[self.current]
        self.current += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def add_token(self, type_: str, literal=None):
        text = self.source[self.start:self.current]
        self.tokens.append(Token(type_, text, literal, self.line, self.col))

    def match(self, expected: str) -> bool:
        if self.is_at_end(): return False
        if self.source[self.current] != expected: return False
        self.current += 1; self.col += 1
        return True

    def peek(self) -> str:
        if self.is_at_end(): return "\0"
        return self.source[self.current]

    def peek_next(self) -> str:
        if self.current + 1 >= len(self.source): return "\0"
        return self.source[self.current + 1]

    # scanning
    def scan_token(self):
        c = self.advance()

        if c in " \t": return

        if c == "\n":
            self.add_token(TokenType.NEWLINE); return

        if c == "/":
            nxt = self.peek()
            if nxt == "/":
                while self.peek() != "\n" and not self.is_at_end():
                    self.advance()
                return
            if nxt == "*":
                self.advance()
                self.block_comment(); return
            if self.match("="): self.add_token(TokenType.SLASH_EQUAL)
            else: self.add_token(TokenType.SLASH)
            return

        # longest-match

        if c == "+":
            if self.match("+"): self.add_token(TokenType.PLUS_PLUS); return
            if self.match("="): self.add_token(TokenType.PLUS_EQUAL); return
            self.add_token(TokenType.PLUS); return
            # self.add_token(TokenType.PLUS); return   # (alt path)

        if c == "-":
            if self.match("-"): self.add_token(TokenType.MINUS_MINUS); return
            if self.match("="): self.add_token(TokenType.MINUS_EQUAL); return
            self.add_token(TokenType.MINUS); return
            # if self.match("="): self.add_token(TokenType.MINUS_EQUAL); return  # similar

        if c == "*":
            if self.match("*"):
                if self.match("="):
                    self.add_token(TokenType.STAR_STAR_EQUAL); return
                self.add_token(TokenType.STAR_STAR); return
            if self.match("="): self.add_token(TokenType.STAR_EQUAL); return
            self.add_token(TokenType.STAR); return

        if c == "%":
            if self.match("="): self.add_token(TokenType.PERCENT_EQUAL); return
            self.add_token(TokenType.PERCENT); return

        if c == "&":
            if self.match("&"): self.add_token(TokenType.AND_AND); return
            raise LexerError(f"Unexpected '&' at line {self.line}")

        if c == "|":
            if self.match("|"): self.add_token(TokenType.OR_OR); return
            raise LexerError(f"Unexpected '|' at line {self.line}")

        if c == "=":
            if self.match("="): self.add_token(TokenType.EQUAL_EQUAL)
            else: self.add_token(TokenType.EQUAL); return
            return

        if c == "!":
            if self.match("="): self.add_token(TokenType.BANG_EQUAL)
            else: self.add_token(TokenType.BANG); return
            return

        if c == ">":
            if self.match("="): self.add_token(TokenType.GREATER_EQUAL)
            else: self.add_token(TokenType.GREATER); return
            return

        if c == "<":
            if self.match("="): self.add_token(TokenType.LESS_EQUAL)
            else: self.add_token(TokenType.LESS); return
            return

        single = {
            "(": TokenType.LEFT_PAREN, ")": TokenType.RIGHT_PAREN,
            "{": TokenType.LEFT_BRACE, "}": TokenType.RIGHT_BRACE,
            ",": TokenType.COMMA, ".": TokenType.DOT,
            ";": TokenType.SEMICOLON, ":": TokenType.COLON,
        }
        if c in single:
            self.add_token(single[c]); return

        if c == '"' or c == "'":
            if c == "'":
                lit = self.char_literal()
                self.add_token(TokenType.CHAR, lit); return
            self.string(c); return

        if c.isdigit():
            self.number(); return

        if c.isalpha() or c == "_":
            self.identifier_or_keyword(); return

        raise LexerError(f"Unexpected character {c!r} at line {self.line} col {self.col}")

    def block_comment(self):
        while not self.is_at_end():
            ch = self.advance()
            if ch == "*" and self.peek() == "/":
                self.advance(); return
        # ok if EOF

    def string(self, quote: str):
        value_chars = []
        while not self.is_at_end() and self.peek() != quote:
            ch = self.advance()
            if ch == "\\":
                nxt = self.advance()
                mapping = {"n":"\n","t":"\t","r":"\r","\\":"\\", '"':'"', "'":"'"}
                value_chars.append(mapping.get(nxt, nxt))
            else:
                value_chars.append(ch)
        if self.is_at_end():
            raise LexerError(f"Unterminated string at line {self.line}")
        self.advance()
        self.add_token(TokenType.STRING, "".join(value_chars))

    def char_literal(self) -> str:
        ch = self.advance()
        if ch == "\\":
            esc = self.advance()
            mapping = {"n":"\n","t":"\t","r":"\r","\\":"\\","'":"'", '"':'"'}
            val = mapping.get(esc, esc)
        else:
            val = ch
        if self.peek() != "'":
            while not self.is_at_end() and self.peek() not in ["'", "\n"]:
                self.advance()
            if self.peek() == "'":
                self.advance()
            raise LexerError(f"Invalid char literal at line {self.line}")
        self.advance()
        return val

    def number(self):
        while self.peek().isdigit(): self.advance()
        if self.peek() == "." and self.peek_next().isdigit():
            self.advance()
            while self.peek().isdigit(): self.advance()
            text = self.source[self.start:self.current]
            self.add_token(TokenType.FLOAT, float(text))
        else:
            text = self.source[self.start:self.current]
            self.add_token(TokenType.INT, int(text))

    def identifier_or_keyword(self):
        while self.peek().isalnum() or self.peek() == "_":
            self.advance()
        text = self.source[self.start:self.current]
        lower = text.lower()

        if lower in PRIMITIVE_TYPES:
            self.tokens.append(Token(TokenType.TYPE, text, lower, self.line, self.col)); return

        if lower == "null":
            self.tokens.append(Token(TokenType.NULL, text, None, self.line, self.col)); return

        ttype = KEYWORDS.get(lower)
        if ttype == TokenType.BOOL:
            lit = True if lower == "true" else False
            self.tokens.append(Token(TokenType.BOOL, text, lit, self.line, self.col)); return
        if ttype is not None:
            self.tokens.append(Token(ttype, text, None, self.line, self.col)); return

        self.tokens.append(Token(TokenType.IDENTIFIER, text, None, self.line, self.col))
