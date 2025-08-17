from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

class TokenType:
    LEFT_PAREN = "LEFT_PAREN"; RIGHT_PAREN = "RIGHT_PAREN"
    LEFT_BRACE = "LEFT_BRACE"; RIGHT_BRACE = "RIGHT_BRACE"
    COMMA = "COMMA"; DOT = "DOT"; MINUS = "MINUS"; PLUS = "PLUS"
    SEMICOLON = "SEMICOLON"; SLASH = "SLASH"; STAR = "STAR"
    PERCENT = "PERCENT"; COLON = "COLON"; EQUAL = "EQUAL"
    BANG = "BANG"; GREATER = "GREATER"; LESS = "LESS"

    EQUAL_EQUAL = "EQUAL_EQUAL"; BANG_EQUAL = "BANG_EQUAL"
    GREATER_EQUAL = "GREATER_EQUAL"; LESS_EQUAL = "LESS_EQUAL"

    PLUS_EQUAL = "PLUS_EQUAL"; MINUS_EQUAL = "MINUS_EQUAL"
    STAR_EQUAL = "STAR_EQUAL"; SLASH_EQUAL = "SLASH_EQUAL"
    PERCENT_EQUAL = "PERCENT_EQUAL"

    PLUS_PLUS = "PLUS_PLUS"; MINUS_MINUS = "MINUS_MINUS"

    STAR_STAR = "STAR_STAR"; STAR_STAR_EQUAL = "STAR_STAR_EQUAL"

    AND_AND = "AND_AND"; OR_OR = "OR_OR"

    IDENTIFIER = "IDENTIFIER"; STRING = "STRING"
    INT = "INT"; FLOAT = "FLOAT"; BOOL = "BOOL"
    CHAR = "CHAR"; NULL = "NULL"

    AND = "AND"; OR = "OR"; NOT = "NOT"
    IF = "IF"; ELSE = "ELSE"; WHILE = "WHILE"
    FOR = "FOR"; RETURN = "RETURN"; FUNCTION = "FUNCTION"; FN = "FN"

    TYPE = "TYPE"
    NEWLINE = "NEWLINE"; EOF = "EOF"

KEYWORDS = {
    "and": TokenType.AND, "or": TokenType.OR, "not": TokenType.NOT,
    "if": TokenType.IF, "else": TokenType.ELSE, "while": TokenType.WHILE,
    "for": TokenType.FOR, "return": TokenType.RETURN,
    "function": TokenType.FUNCTION, "fn": TokenType.FN,
    "true": TokenType.BOOL, "false": TokenType.BOOL,
}

PRIMITIVE_TYPES = {"byte","short","int","long","bool","float","double","char","string"}

@dataclass
class Token:
    type: str
    lexeme: str
    literal: Optional[object]
    line: int
    column: int
    def __repr__(self) -> str:
        lit = f", {self.literal!r}" if self.literal is not None else ""
        return f"Token({self.type}, {self.lexeme!r}{lit}, line={self.line}, col={self.column})"
