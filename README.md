# Compiler Construction Project Report Spring 2026

## Team Members

- Muhammad Mahad (408576)
- Abdul Moiz (375299)
- Bashar (366006)

## 1. Introduction

This document presents the design and implementation of a modular compiler for a subset of the C programming language. The compiler is implemented entirely in Python and features Lexical Analysis, Syntax Analysis (Recursive Descent Parsing), Semantic Analysis (Symbol Table for scope checking), Code Optimization (Constant Folding and Dead Code Elimination), Intermediate Representation (TAC) generation, and finally LLVM IR Backend generation.

## 2. Subset Definition & Grammar

### Features Supported

- **Data Types**: `int`, `float`, `double`, and `void` (function return type only), with implicit conversions between numeric types on assignment, arguments, returns and mixed arithmetic
- **Expressions**: Arithmetic (`+`, `-`, `*`, `/`, `%`), Relational (`==`, `!=`, `<`, `>`, `<=`, `>=`), Logical (`&&`, `||`, `!`) with short-circuit evaluation, prefix and postfix `++` / `--`
- **Control Flow**: `if-else`, `while`, `for` loops (with a declaration in the init clause, and any clause may be empty)
- **Functions**: Parameter passing, return statements, recursion, `void` functions and `f(void)` parameter lists
- **Variables**: Block-scoped locals with shadowing, and global variables and arrays with constant initializers
- **Comments**: `//` line comments and `/* */` block comments
- **Innovation Features**: 1D Arrays, Constant Folding, Dead Code Elimination

### Context-Free Grammar (Subset)

```cpp
Program   -> Decl*
Decl      -> Type ID ( '(' Params ')' Block | '[' NUMBER ']' ';' | [ '=' Expr ] ';' )
           | 'void' ID '(' Params ')' Block
Type      -> 'int' | 'float' | 'double'
Params    -> 'void' | [ Type ID { ',' Type ID } ]
Block     -> '{' ( LocalDecl | Stmt )* '}'
LocalDecl -> Type ID ( '[' NUMBER ']' | [ '=' Expr ] ) ';'
Stmt      -> IfStmt | WhileStmt | ForStmt | ReturnStmt | ExprStmt | Block
IfStmt    -> 'if' '(' Expr ')' Stmt [ 'else' Stmt ]
WhileStmt -> 'while' '(' Expr ')' Stmt
ForStmt   -> 'for' '(' ( Type ID [ '=' Expr ] ';' | ExprStmt | ';' ) [ Expr ] ';' [ Assign ] ')' Stmt
ReturnStmt-> 'return' [ Expr ] ';'
ExprStmt  -> Assign ';'
Assign    -> ID '=' Assign | ID '[' Expr ']' '=' Assign | Expr
Expr      -> LogicalOr
LogicalOr -> LogicalAnd { '||' LogicalAnd }
LogicalAnd-> Equality { '&&' Equality }
Equality  -> Relational { ( '==' | '!=' ) Relational }
Relational-> Additive { ( '<' | '>' | '<=' | '>=' ) Additive }
Additive  -> Term { ( '+' | '-' ) Term }
Term      -> Unary { ( '*' | '/' | '%' ) Unary }
Unary     -> ( '-' | '!' ) Unary | ( '++' | '--' ) ID | Primary
Primary   -> NUMBER | ID [ '++' | '--' ] | ID '(' [ Expr { ',' Expr } ] ')' | ID '[' Expr ']' | '(' Expr ')'
```

## 3. Design of Compiler Phases

1. **Lexical Analyzer (`lexer.py`)**: Tokenizes the input code using regular expressions to match keywords, numbers, identifiers, and symbols. Comments are skipped while keeping line numbers accurate for error messages.
2. **Syntax Analyzer (`parser.py`)**: Uses Recursive Descent Parsing to build an Abstract Syntax Tree (AST). It incorporates assignments directly into expressions to support standard C `for` loops.
3. **Semantic Analyzer (`semantic.py`)**: Traverses the AST with a stack-based Symbol Table to enforce variable scoping, duplicate declarations, array access checks, argument counts, `void` usage and constant global initializers.
4. **Optimizer (`optimizer.py`)**: Performs Constant Folding on arithmetic expressions and eliminates dead code (e.g. `if(0)` blocks or `while(0)`). Folding follows C semantics: integer division and remainder truncate toward zero and integer results wrap at 32 bits.
5. **TAC Generator (`tac.py`)**: A post-order AST traversal to generate flat Three-Address Code with explicit labels and temporaries.
6. **LLVM Backend (`codegen.py`)**: Traverses the AST to generate standard LLVM Intermediate Representation (`.ll`). Every local variable gets one stack slot (`alloca`) in the function's entry block, accessed through loads and stores; a scope stack resolves shadowed names. `&&` and `||` are lowered to branches joined by a `phi` node so the right operand is only evaluated when needed.

## 4. Limitations

- Single-dimensional arrays only, with no array initializers.
- Pointers, structs, `char` and string literals are not supported, so there is no I/O; programs report results through their exit code.
- No compound assignment (`+=` etc.), `break`, `continue`, `do-while` or `switch`.
- Floating-point literals need digits before the decimal point (`0.5`, not `.5`) and cannot use exponents (`1e5`).
- No bounds checking on array accesses.

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

### Automated test suite

`tests/run_tests.py` runs 16 end-to-end programs and 11 error cases:

- **`tests/programs/`**: `arrays.c`, `comments.c`, `comparisons.c`, `early_return.c`, `floats.c`, `folding.c`, `for_loops.c`, `general.c`, `globals.c`, `incdec.c`, `logical.c`, `recursion.c`, `shadowing.c`, `short_circuit.c`, `stack_growth.c`, `void_functions.c`
- **`tests/errors/`**: `global_non_constant.c`, `incdec_array.c`, `invalid_identifier.c`, `missing_semicolon.c`, `redeclared_var.c`, `undeclared_var.c`, `unterminated_comment.c`, `void_return_value.c`, `void_used_as_value.c`, `void_variable.c`, `wrong_arg_count.c`

### Worked example (`compiler/test.c`)

This program exercises arithmetic, constant folding (`5 + 3` becomes `8`), loops, dead code elimination (the `if (0)` block is removed), function calls and arrays. The compiled executable exits with status 165 (30 + 80 + 55).

**Source Code:**

```c
int arithmetic() {
    int a = 10;
    int b = 5 + 3; 
    int c = a * b;
    return c;
}

int loops() {
    int sum = 0;
    int i = 0;
    while (i < 10) {
        sum = sum + i;
        i = i + 1;
    }
    
    int j;
    for (j = 0; j < 5; j = j + 1) {
        sum = sum + j;
    }
    
    if (0) {
        sum = 0;
    }
    
    return sum;
}

int add(int x, int y) {
    return x + y;
}

int main() {
    int arr[5];
    arr[0] = 10;
    arr[1] = 20;
    
    int result = add(arr[0], arr[1]);
    return result + arithmetic() + loops();
}
```

**Generated TAC (`compiler/output.tac`):**

```text
func arithmetic:
begin_func
a = 10
b = 8
t1 = a * b
c = t1
return c
end_func

func loops:
begin_func
sum = 0
i = 0
L1:
t2 = i < 10
if_false t2 goto L2
t3 = sum + i
sum = t3
t4 = i + 1
i = t4
goto L1
L2:
j = 0
L3:
t5 = j < 5
if_false t5 goto L4
t6 = sum + j
sum = t6
t7 = j + 1
j = t7
goto L3
L4:
return sum
end_func

func add:
begin_func
t8 = x + y
return t8
end_func

func main:
begin_func
alloc_array arr, 5
arr[0] = 10
arr[1] = 20
t9 = arr[0]
t10 = arr[1]
param t9
param t10
t11 = call add, 2
result = t11
t12 = call arithmetic, 0
t13 = result + t12
t14 = call loops, 0
t15 = t13 + t14
return t15
end_func
```

**Generated LLVM IR (`compiler/output.ll`):**

```llvm
; LLVM IR Generated by Custom Compiler
declare i32 @printf(i8*, ...)

define i32 @arithmetic() {
entry:
  %a.addr1 = alloca i32
  %b.addr2 = alloca i32
  %c.addr3 = alloca i32
  store i32 10, i32* %a.addr1
  store i32 8, i32* %b.addr2
  %1 = load i32, i32* %a.addr1
  %2 = load i32, i32* %b.addr2
  %3 = mul i32 %1, %2
  store i32 %3, i32* %c.addr3
  %4 = load i32, i32* %c.addr3
  ret i32 %4
}

define i32 @loops() {
entry:
  %sum.addr1 = alloca i32
  %i.addr2 = alloca i32
  %j.addr3 = alloca i32
  store i32 0, i32* %sum.addr1
  store i32 0, i32* %i.addr2
  br label %L1
L1:
  %1 = load i32, i32* %i.addr2
  %2 = icmp slt i32 %1, 10
  %3 = zext i1 %2 to i32
  %4 = icmp ne i32 %3, 0
  br i1 %4, label %L2, label %L3
L2:
  %5 = load i32, i32* %sum.addr1
  %6 = load i32, i32* %i.addr2
  %7 = add i32 %5, %6
  store i32 %7, i32* %sum.addr1
  %8 = load i32, i32* %i.addr2
  %9 = add i32 %8, 1
  store i32 %9, i32* %i.addr2
  br label %L1
L3:
  store i32 0, i32* %j.addr3
  br label %L4
L4:
  %10 = load i32, i32* %j.addr3
  %11 = icmp slt i32 %10, 5
  %12 = zext i1 %11 to i32
  %13 = icmp ne i32 %12, 0
  br i1 %13, label %L5, label %L6
L5:
  %14 = load i32, i32* %sum.addr1
  %15 = load i32, i32* %j.addr3
  %16 = add i32 %14, %15
  store i32 %16, i32* %sum.addr1
  %17 = load i32, i32* %j.addr3
  %18 = add i32 %17, 1
  store i32 %18, i32* %j.addr3
  br label %L4
L6:
  %19 = load i32, i32* %sum.addr1
  ret i32 %19
}

define i32 @add(i32 %x_arg, i32 %y_arg) {
entry:
  %x.addr1 = alloca i32
  %y.addr2 = alloca i32
  store i32 %x_arg, i32* %x.addr1
  store i32 %y_arg, i32* %y.addr2
  %1 = load i32, i32* %x.addr1
  %2 = load i32, i32* %y.addr2
  %3 = add i32 %1, %2
  ret i32 %3
}

define i32 @main() {
entry:
  %arr.addr1 = alloca [5 x i32]
  %result.addr2 = alloca i32
  %1 = getelementptr [5 x i32], [5 x i32]* %arr.addr1, i32 0, i32 0
  store i32 10, i32* %1
  %2 = getelementptr [5 x i32], [5 x i32]* %arr.addr1, i32 0, i32 1
  store i32 20, i32* %2
  %3 = getelementptr [5 x i32], [5 x i32]* %arr.addr1, i32 0, i32 0
  %4 = load i32, i32* %3
  %5 = getelementptr [5 x i32], [5 x i32]* %arr.addr1, i32 0, i32 1
  %6 = load i32, i32* %5
  %7 = call i32 @add(i32 %4, i32 %6)
  store i32 %7, i32* %result.addr2
  %8 = load i32, i32* %result.addr2
  %9 = call i32 @arithmetic()
  %10 = add i32 %8, %9
  %11 = call i32 @loops()
  %12 = add i32 %10, %11
  ret i32 %12
}
```
