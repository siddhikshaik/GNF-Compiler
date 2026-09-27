# GNF Compiler Lab — Final

A complete educational CFG → Greibach Normal Form (GNF) laboratory prototype.

## What it does
- Parses a CFG entered by the user.
- Detects variables and terminals.
- Eliminates epsilon productions (with correct nullable-variable expansion).
- Eliminates unit productions using unit-closure.
- Removes useless symbols.
- Eliminates indirect and immediate left recursion using ordered substitution.
- Converts remaining productions to terminal-leading GNF form.
- Validates every final production.
- Shows every transformation stage.
- Includes animated pipeline, hover/click effects, grammar highlighting and a final report.

## Run on Windows PowerShell
```powershell
py -m pip install -r requirements.txt
py app.py
```

Open:
http://127.0.0.1:5000

## Grammar input
You can write either compact character-style grammars:
```text
S -> AB | a
A -> a
B -> b
```

or spaced symbols:
```text
S -> A B | a
A -> a
B -> b
```

Variables are taken from the left-hand sides. Other symbols are treated as terminals.

## Algorithm
The engine uses the standard constructive route:
1. Parse grammar
2. Remove epsilon productions
3. Remove unit productions
4. Remove useless symbols
5. Eliminate indirect + immediate left recursion
6. Order variables and substitute earlier-variable-leading productions
7. Continue substitution until every RHS starts with a terminal
8. Validate GNF

GNF is checked as:
A -> a A1 A2 ... Ak
where `a` is a terminal and the remaining symbols, if any, are variables.
The usual exception for the start symbol's epsilon production is supported when explicitly enabled by the algorithm.

## Important
The application is intended as a college project and demonstration tool. It uses exact symbolic transformations and records intermediate grammars. For very large grammars, the number of productions can grow substantially during normal CFG normalization.
