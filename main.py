from __future__ import annotations
import sys, traceback
from lexer import Lexer, LexerError
from parser import Parser, ParseError
from runtime import Interpreter, Environment, RuntimeError_
from stdlib import install_builtins

def run_source(source: str):
    try:
        parser = Parser.from_source(source)
        stmts = parser.parse()
        if parser.errors:
            print("Parse warnings:")
            for e in parser.errors:
                print("  -", e)
        env = Environment()
        install_builtins(env)
        interp = Interpreter(env)
        interp.run(stmts)
    except (LexerError, ParseError) as e:
        print("Syntax error:", e)
    except RuntimeError_ as e:
        print("Runtime error:", e)
    except Exception:
        traceback.print_exc()

def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <file.language>")
        return
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        source = f.read()
    run_source(source)

if __name__ == "__main__":
    main()
