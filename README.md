# Compiler Construction Project Report Spring 2026

## Team Members

- Muhammad Mahad (408576)
- Abdul Moiz (375299)
- Bashar (366006)

## 1. Introduction

This document presents the design and implementation of a modular compiler for a subset of the C programming language. The compiler is implemented entirely in Python and features Lexical Analysis, Syntax Analysis (Recursive Descent Parsing), Semantic Analysis (Symbol Table for scope checking), Code Optimization (Constant Folding and Dead Code Elimination), Intermediate Representation (TAC) generation, and finally LLVM IR Backend generation.

## 2. Subset Definition & Grammar

### Features Supported

- **Data Types**: `int`, `float`, `double`
- **Expressions**: Arithmetic (`+`, `-`, `*`, `/`, `%`), Relational (`==`, `!=`, `<`, `>`, `<=`, `>=`), Logical (`&&`, `||`, `!`)
- **Control Flow**: `if-else`, `while`, `for` loops
- **Functions**: Parameter passing and return statements
- **Innovation Features**: 1D Arrays, Constant Folding, Dead Code Elimination

### Context-Free Grammar (Subset)

```cpp
Program -> Decl*
Decl -> Type ID ( '(' Params ')' Block | '[' NUMBER ']' ';' | [ '=' Expr ] ';' )
Block -> '{' Stmt* '}'
Stmt -> IfStmt | WhileStmt | ForStmt | ReturnStmt | ExprStmt | Block
IfStmt -> 'if' '(' Expr ')' Stmt [ 'else' Stmt ]
WhileStmt -> 'while' '(' Expr ')' Stmt
ForStmt -> 'for' '(' ExprStmt Expr ';' Expr ')' Stmt
ExprStmt -> [ ID '=' Expr | ID '[' Expr ']' '=' Expr ] ';' | Expr ';'
Expr -> LogicalOr
```

## 3. Design of Compiler Phases

1. **Lexical Analyzer (`lexer.py`)**: Tokenizes the input code using regular expressions to match keywords, numbers, identifiers, and symbols.
2. **Syntax Analyzer (`parser.py`)**: Uses Recursive Descent Parsing to build an Abstract Syntax Tree (AST). It incorporates assignments directly into expressions to support standard C `for` loops.
3. **Semantic Analyzer (`semantic.py`)**: Traverses the AST with a stack-based Symbol Table to enforce variable scoping, duplicate declarations, and array access checks.
4. **Optimizer (`optimizer.py`)**: Performs Constant Folding on arithmetic expressions and eliminates dead code (e.g. `if(0)` blocks or `while(0)`).
5. **TAC Generator (`tac.py`)**: A post-order AST traversal to generate flat Three-Address Code with explicit labels and temporaries.
6. **LLVM Backend (`codegen.py`)**: Traverses the AST to generate standard LLVM Intermediate Representation (`.ll`). It handles memory allocation (`alloca`), loads, and stores to properly reflect local scoping.

## 4. Limitations

- Single-dimensional arrays only.
- Pointers and structs are not supported.
- Only simple typing (implicit promotion between int and float is limited).

## 5. Compilation Instructions

The compiler is designed to run in a standard Python 3 environment without external dependencies.

1. Place all source files (`lexer.py`, `parser.py`, `ast_nodes.py`, `semantic.py`, `optimizer.py`, `tac.py`, `codegen.py`, `main.py`) in a directory.
2. Run the compiler on a C source file:

   ```bash
   python main.py input.c
   ```

3. The compiler will produce `output.tac` (Three-Address Code) and `output.ll` (LLVM IR).
4. To compile the LLVM IR to a native executable, use clang:

   ```bash
   clang output.ll -o output.exe
   ./output.exe
   ```

5. To run the automated test suite (requires `clang` on your PATH):

   ```bash
   python tests/run_tests.py
   ```

   Each program in `tests/programs/` is compiled both natively by clang and through this compiler, and the two executables' exit codes must match. Each file in `tests/errors/` must be rejected with a compiler error. Pass a substring to run only matching tests, e.g. `python tests/run_tests.py float`.

## 6. Test Cases & Output

### Test Case: Simple Arithmetic and Constant Folding (`test1_arithmetic.c`)

**Source Code:**

```c
{code}
```

**Generated TAC:**

```c
{chr(10).join(tac)}
```

**Generated LLVM IR:**

```llvm
{llvm}
```

---

### Test Case: Loops and Dead Code Elimination (`test2_loops.c`)

**Source Code:**

```c
{code}
```

**Generated TAC:**

```c
{chr(10).join(tac)}
```

**Generated LLVM IR:**

```llvm
{llvm}
```

---

### Test Case: Function Calls and Arrays (`test3_functions_arrays.c`)

**Source Code:**

```c
{code}
```

**Generated TAC:**

```c
{chr(10).join(tac)}
```

**Generated LLVM IR:**

```llvm
{llvm}
```
