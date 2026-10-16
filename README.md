# Compiler Construction Project Report Spring 2026

## Team Members

- Muhammad Mahad (408576)
- Abdul Moiz (375299)
- Bashar (366006)

## 1. Introduction

This document presents the design and implementation of a modular compiler for a subset of the C programming language. The compiler is implemented entirely in Python and features Lexical Analysis, Syntax Analysis (Recursive Descent Parsing), Semantic Analysis (Symbol Table for scope checking), Code Optimization (Constant Folding and Dead Code Elimination), Intermediate Representation (TAC) generation, and finally LLVM IR Backend generation.

## 2. Subset Definition & Grammar

### Features Supported

- **Data Types**: `int`, `float`, `double`, pointers to them at any depth (`int *`, `double **`), and `void` (function return type only), with implicit conversions between numeric types on assignment, arguments, returns and mixed arithmetic
- **Structs**: `struct` definitions with number, pointer, nested struct and fixed-size array fields (including `struct Node *next` for linked structures); local, global and array-of-struct variables; `.` and `->` access; whole-struct copies, arguments and return values
- **Initializer lists**: `struct Point p = {1, 2};`, nested lists, brace elision (`struct Rect r = {0, 0, 3, 4};`), arrays such as `int a[] = {1, 2, 3}` with the size taken from the list, arrays of structs, and designated initializers such as `{ .y = 2, .corner.x = 1 }` and `{ [4] = 1 }`, after which positional values continue from the next member. Members left out are zero, as in C, a later value for the same member replaces an earlier one, and global initializers must be constants
- **Pointers**: `&x` and `&a[i]`, `*p` for reading and writing, `p[i]`, pointer arithmetic (`p + n`, `p - n`, `p++`, and `p - q` for the number of elements between two pointers), comparisons, null checks against `0`, arrays that decay to pointers, and `int a[]` parameters
- **Expressions**: Arithmetic (`+`, `-`, `*`, `/`, `%`), Relational (`==`, `!=`, `<`, `>`, `<=`, `>=`), Logical (`&&`, `||`, `!`) with short-circuit evaluation, prefix and postfix `++` / `--` on variables, array elements, struct members and `*p`, and assignment with `=`, `+=`, `-=`, `*=`, `/=` and `%=`
- **Control Flow**: `if-else`, `switch` (with fall-through and `default`), `while`, `do-while`, `for` loops (with a declaration in the init clause, and any clause may be empty), `break` and `continue`
- **Functions**: Parameter passing, return statements, recursion, `void` functions and `f(void)` parameter lists
- **Variables**: Block-scoped locals with shadowing, and global variables and arrays with constant initializers
- **Comments**: `//` line comments and `/* */` block comments
- **Innovation Features**: 1D Arrays, Constant Folding, Dead Code Elimination

### Context-Free Grammar (Subset)

```cpp
Program   -> ( StructDef | Decl )*
StructDef -> 'struct' ID '{' { Type ID [ '[' NUMBER ']' ] ';' } '}' ';'
Decl      -> Type ID ( '(' Params ')' Block | ArrayPart ';' | [ '=' Init ] ';' )
ArrayPart -> '[' [ NUMBER ] ']' [ '=' InitList ]
Init      -> Expr | InitList
InitList  -> '{' [ Item { ',' Item } [ ',' ] ] '}'
Item      -> [ { '.' ID | '[' Expr ']' } '=' ] Init
           | 'void' ID '(' Params ')' Block
Type      -> ( 'int' | 'float' | 'double' | 'struct' ID ) { '*' }
Params    -> 'void' | [ Param { ',' Param } ]
Param     -> Type ID [ '[' [ NUMBER ] ']' ]
Block     -> '{' ( LocalDecl | Stmt )* '}'
LocalDecl -> Type ID ( ArrayPart | [ '=' Init ] ) ';'
Stmt      -> IfStmt | SwitchStmt | WhileStmt | DoWhileStmt | ForStmt | ReturnStmt | 'break' ';' | 'continue' ';' | ExprStmt | Block
IfStmt    -> 'if' '(' Expr ')' Stmt [ 'else' Stmt ]
SwitchStmt -> 'switch' '(' Expr ')' '{' { ( 'case' Expr | 'default' ) ':' { LocalDecl | Stmt } } '}'
WhileStmt -> 'while' '(' Expr ')' Stmt
DoWhileStmt -> 'do' Stmt 'while' '(' Expr ')' ';'
ForStmt   -> 'for' '(' ( Type ID [ '=' Expr ] ';' | ExprStmt | ';' ) [ Expr ] ';' [ Assign ] ')' Stmt
ReturnStmt-> 'return' [ Expr ] ';'
ExprStmt  -> Assign ';'
Assign    -> LValue AssignOp Assign | Expr
LValue    -> Postfix | '*' Unary
AssignOp  -> '=' | '+=' | '-=' | '*=' | '/=' | '%='
Expr      -> LogicalOr
LogicalOr -> LogicalAnd { '||' LogicalAnd }
LogicalAnd-> Equality { '&&' Equality }
Equality  -> Relational { ( '==' | '!=' ) Relational }
Relational-> Additive { ( '<' | '>' | '<=' | '>=' ) Additive }
Additive  -> Term { ( '+' | '-' ) Term }
Term      -> Unary { ( '*' | '/' | '%' ) Unary }
Unary     -> ( '-' | '!' | '*' | '&' | '++' | '--' ) Unary | Postfix
Postfix   -> Primary { '[' Expr ']' | '.' ID | '->' ID } [ '++' | '--' ]
Primary   -> NUMBER | ID | ID '(' [ Expr { ',' Expr } ] ')' | '(' Expr ')'
```

## 3. Design of Compiler Phases

1. **Lexical Analyzer (`lexer.py`)**: Tokenizes the input code using regular expressions to match keywords, numbers, identifiers, and symbols. Comments are skipped while keeping line numbers accurate for error messages.
2. **Syntax Analyzer (`parser.py`)**: Uses Recursive Descent Parsing to build an Abstract Syntax Tree (AST). It incorporates assignments directly into expressions to support standard C `for` loops.
3. **Semantic Analyzer (`semantic.py`)**: Traverses the AST with a stack-based Symbol Table to enforce variable scoping, duplicate declarations, array access checks, argument counts, `void` usage and constant global initializers. It also works out the type of every expression (`int`, `float`, `double`, a pointer type or `void`) using C's usual arithmetic conversions and pointer rules, and rejects what C rejects: `%` on floating-point operands, non-integer array indexes, sizes and `switch` values, dereferencing a non-pointer, mixing pointers and integers (other than the null constant `0`), and invalid pointer arithmetic such as adding two pointers.
4. **Optimizer (`optimizer.py`)**: Performs Constant Folding on arithmetic expressions and eliminates dead code (e.g. `if(0)` blocks or `while(0)`). Folding follows C semantics: integer division and remainder truncate toward zero and integer results wrap at 32 bits.
5. **TAC Generator (`tac.py`)**: A post-order AST traversal to generate flat Three-Address Code with explicit labels and temporaries.
6. **LLVM Backend (`codegen.py`)**: Traverses the AST to generate standard LLVM Intermediate Representation (`.ll`). Every local variable gets one stack slot (`alloca`) in the function's entry block, accessed through loads and stores; a scope stack resolves shadowed names. `&&` and `||` are lowered to branches joined by a `phi` node so the right operand is only evaluated when needed.

## 4. Limitations

- Single-dimensional arrays only.
- `char`, string literals and unions are not supported, so there is no I/O; programs report results through their exit code.
- Structs must be defined at the top level before they are used, even through a pointer, and have no `sizeof`.
- An initializer list with more values than its struct or array has room for is an error, as the C standard requires; clang only warns and drops the extra values.
- Pointers have no `void *`, casts or function pointers, and `&` of a whole array or array field isn't supported (the name on its own already points to its first element).
- Assigning between different pointer types is an error. Clang only warns about it, but GCC 14 and later reject it too.
- Conversions between `int`, `float` and `double` happen implicitly as in C, without warnings for narrowing (for example, assigning a `double` to an `int`).
- Zero-length arrays, a GNU extension that clang accepts, are rejected as in ISO C.
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

### Website

The `public/` folder holds a landing page and an in-browser compiler (`/compiler`) that shows the tokens, syntax tree, three-address code and LLVM IR for any program. The pages call `api/compile.py`, a Vercel serverless function that runs the compiler from `compiler/pipeline.py`. Vercel has no clang, so the website shows the output but doesn't run the program.

- **Run it locally:** `python dev_server.py`, then open http://127.0.0.1:8000. This serves the same pages and API function that Vercel deploys.
- **Test it:** `python tests/test_web.py` checks the pages, the examples and the API's responses. It doesn't need clang.
- **Deploy it:** import the repository in Vercel with the framework preset set to "Other". `vercel.json` sets everything else, so leave the build and output settings empty. There are no dependencies to install.

## 6. Test Cases & Output

### Automated test suite

`python tests/run_tests.py` runs 117 tests, and `python tests/test_web.py` checks the website and its API separately.

- **27 programs** in `tests/programs/` and **9 website examples** in `public/examples/` are each compiled twice: natively by clang, and through this compiler to LLVM IR that clang then builds. The test passes when both executables exit with the same status, so every expected result comes from a real C compiler.
- **81 error cases** in `tests/errors/` must be rejected with a lexer, parser or semantic error. Where a file marks a line with a `// error` comment, the error must be reported on that line. An internal crash counts as a failure.

| Area | Program tests |
| :--- | :--- |
| Expressions and types | `comparisons.c`, `logical.c`, `short_circuit.c`, `floats.c`, `implicit_conversions.c`, `folding.c` |
| Statements and control flow | `early_return.c`, `for_loops.c`, `break_continue.c`, `break_search.c`, `do_while.c`, `switch.c` |
| Assignment and increments | `compound_assignment.c`, `incdec.c`, `incdec_places.c` |
| Variables, scope and functions | `shadowing.c`, `globals.c`, `void_functions.c`, `recursion.c`, `comments.c`, `stack_growth.c` |
| Arrays and pointers | `arrays.c`, `pointers.c` |
| Structs and initializers | `structs.c`, `init_lists.c`, `designated_initializers.c` |
| Combined | `general.c` |
| Website examples | `calculator.c`, `fibonacci.c`, `floats.c`, `globals.c`, `pointers.c`, `primes.c`, `short_circuit.c`, `structs.c`, `tour.c` |

<details>
<summary>Error tests by area</summary>

| Area | Error tests |
| :--- | :--- |
| Lexical and syntax errors (14) | `array_without_size.c`, `assign_to_value.c`, `break_missing_semicolon.c`, `case_outside_switch.c`, `compound_missing_operand.c`, `do_while_missing_semicolon.c`, `do_without_while.c`, `invalid_identifier.c`, `missing_semicolon.c`, `struct_defined_in_function.c`, `switch_statement_before_case.c`, `unterminated_comment.c`, `void_pointer.c`, `void_variable.c` |
| Names, scopes and functions (12) | `assign_to_function.c`, `compound_undeclared.c`, `do_while_body_scope.c`, `duplicate_function.c`, `duplicate_param.c`, `global_non_constant.c`, `redeclared_var.c`, `undeclared_function.c`, `undeclared_var.c`, `void_return_value.c`, `void_used_as_value.c`, `wrong_arg_count.c` |
| Loops and switch (8) | `break_outside_loop.c`, `continue_outside_loop.c`, `switch_case_not_constant.c`, `switch_continue_outside_loop.c`, `switch_double_value.c`, `switch_duplicate_case.c`, `switch_float_case.c`, `switch_two_defaults.c` |
| Types (10) | `array_as_value.c`, `array_size_float.c`, `array_size_zero.c`, `compound_mod_float.c`, `compound_on_array.c`, `float_index.c`, `float_index_assign.c`, `incdec_array.c`, `mod_double.c`, `not_an_array.c` |
| Pointers (10) | `address_of_array.c`, `address_of_value.c`, `deref_assign_non_pointer.c`, `deref_non_pointer.c`, `incompatible_pointers.c`, `int_to_pointer.c`, `pointer_argument_type.c`, `pointer_multiply.c`, `pointer_plus_pointer.c`, `pointer_to_int.c` |
| Structs (13) | `struct_arithmetic.c`, `struct_arrow_on_struct.c`, `struct_as_condition.c`, `struct_assign_array_field.c`, `struct_compare.c`, `struct_contains_itself.c`, `struct_dot_on_pointer.c`, `struct_duplicate_field.c`, `struct_increment.c`, `struct_mismatched_types.c`, `struct_redefined.c`, `struct_unknown_field.c`, `struct_unknown_type.c` |
| Initializers (14) | `designator_field_on_array.c`, `designator_index_on_struct.c`, `designator_not_constant.c`, `designator_out_of_bounds.c`, `designator_runs_past_end.c`, `designator_unknown_field.c`, `designator_wrong_type.c`, `init_array_without_braces.c`, `init_empty_unsized_array.c`, `init_global_not_constant.c`, `init_scalar_list.c`, `init_too_many_elements.c`, `init_too_many_fields.c`, `init_wrong_type.c` |

</details>

### Sample diagnostics

Every error reports the line it was found on, and the website also names the phase that found it. These are the compiler's messages for some of the error tests above:

| Test | Message |
| :--- | :--- |
| `undeclared_var.c` | Undeclared variable 'y' at line 2 |
| `missing_semicolon.c` | Expected SEMI, found RETURN at line 3 |
| `switch_duplicate_case.c` | Duplicate case value 1 (first used on line 4) at line 6 |
| `mod_double.c` | Operands of '%' must be integers, not double and int at line 3 |
| `incompatible_pointers.c` | Initializer of 'f': incompatible pointer types, int* and float* at line 3 |
| `struct_dot_on_pointer.c` | '.' needs a struct, not struct Point*; use '->' on a pointer to a struct at line 8 |
| `init_too_many_fields.c` | Initializer of 'p': too many values for struct Point at line 7 |
| `designator_out_of_bounds.c` | Initializer of 'a': designator [3] is outside int[3] at line 2 |

## 7. Worked Examples

### A tour of the original subset (`compiler/test.c`)

Arithmetic, constant folding (`5 + 3` becomes `8`), loops, dead code elimination (the `if (0)` block is removed), function calls and arrays. This is the program behind `compiler/output.tac` and `compiler/output.ll`. The compiled program exits with status 165.

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

**Three-address code:**

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
if_false t5 goto L5
t6 = sum + j
sum = t6
L4:
t7 = j + 1
j = t7
goto L3
L5:
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

<details>
<summary>LLVM IR</summary>

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
  br i1 %13, label %L5, label %L7
L5:
  %14 = load i32, i32* %sum.addr1
  %15 = load i32, i32* %j.addr3
  %16 = add i32 %14, %15
  store i32 %16, i32* %sum.addr1
  br label %L6
L6:
  %17 = load i32, i32* %j.addr3
  %18 = add i32 %17, 1
  store i32 %18, i32* %j.addr3
  br label %L4
L7:
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

</details>

### Loops with break, continue and compound assignment (`public/examples/primes.c`)

Counts the primes below 50. The inner `for` loop leaves early with `break`, the outer one skips even numbers with `continue`, and both use `+=`. In the TAC, `continue` jumps to the label just before the increment, so `n++` still runs. The compiled program exits with status 15.

```c
// Counts the primes below 50. The inner loop breaks as soon as it finds a
// divisor, and the outer loop uses continue to skip even numbers.
// The program exits with status 15.

int main() {
    int count = 1; // 2 is the only even prime
    for (int n = 3; n < 50; n++) {
        if (n % 2 == 0) {
            continue;
        }
        int is_prime = 1;
        for (int d = 3; d * d <= n; d += 2) {
            if (n % d == 0) {
                is_prime = 0;
                break;
            }
        }
        count += is_prime;
    }
    return count;
}
```

**Three-address code:**

```text
func main:
begin_func
count = 1
n = 3
L1:
t1 = n < 50
if_false t1 goto L3
t2 = n % 2
t3 = t2 == 0
if_false t3 goto L4
goto L2
goto L5
L4:
L5:
is_prime = 1
d = 3
L6:
t4 = d * d
t5 = t4 <= n
if_false t5 goto L8
t6 = n % d
t7 = t6 == 0
if_false t7 goto L9
is_prime = 0
goto L8
goto L10
L9:
L10:
L7:
t8 = d + 2
d = t8
goto L6
L8:
t9 = count + is_prime
count = t9
L2:
t10 = n
n = n + 1
goto L1
L3:
return count
end_func
```

<details>
<summary>LLVM IR</summary>

```llvm
; LLVM IR Generated by Custom Compiler
declare i32 @printf(i8*, ...)

define i32 @main() {
entry:
  %count.addr1 = alloca i32
  %n.addr2 = alloca i32
  %is_prime.addr3 = alloca i32
  %d.addr4 = alloca i32
  store i32 1, i32* %count.addr1
  store i32 3, i32* %n.addr2
  br label %L1
L1:
  %1 = load i32, i32* %n.addr2
  %2 = icmp slt i32 %1, 50
  %3 = zext i1 %2 to i32
  %4 = icmp ne i32 %3, 0
  br i1 %4, label %L2, label %L4
L2:
  %5 = load i32, i32* %n.addr2
  %6 = srem i32 %5, 2
  %7 = icmp eq i32 %6, 0
  %8 = zext i1 %7 to i32
  %9 = icmp ne i32 %8, 0
  br i1 %9, label %L5, label %L7
L5:
  br label %L3
L7:
  store i32 1, i32* %is_prime.addr3
  store i32 3, i32* %d.addr4
  br label %L8
L8:
  %10 = load i32, i32* %d.addr4
  %11 = load i32, i32* %d.addr4
  %12 = mul i32 %10, %11
  %13 = load i32, i32* %n.addr2
  %14 = icmp sle i32 %12, %13
  %15 = zext i1 %14 to i32
  %16 = icmp ne i32 %15, 0
  br i1 %16, label %L9, label %L11
L9:
  %17 = load i32, i32* %n.addr2
  %18 = load i32, i32* %d.addr4
  %19 = srem i32 %17, %18
  %20 = icmp eq i32 %19, 0
  %21 = zext i1 %20 to i32
  %22 = icmp ne i32 %21, 0
  br i1 %22, label %L12, label %L14
L12:
  store i32 0, i32* %is_prime.addr3
  br label %L11
L14:
  br label %L10
L10:
  %23 = load i32, i32* %d.addr4
  %24 = add i32 %23, 2
  store i32 %24, i32* %d.addr4
  br label %L8
L11:
  %25 = load i32, i32* %is_prime.addr3
  %26 = load i32, i32* %count.addr1
  %27 = add i32 %26, %25
  store i32 %27, i32* %count.addr1
  br label %L3
L3:
  %28 = load i32, i32* %n.addr2
  %29 = add i32 %28, 1
  store i32 %29, i32* %n.addr2
  br label %L1
L4:
  %30 = load i32, i32* %count.addr1
  ret i32 %30
}
```

</details>

### A switch statement with fall-through (`public/examples/calculator.c`)

Chooses an operation with `switch`. Cases 3 and 4 share a body, case 5 falls through into case 6, and unknown codes reach `default`. The LLVM IR uses its native `switch` instruction. The compiled program exits with status 128.

```c
// A tiny calculator: each operation code picks a case. Codes 3 and 4 share
// a body, code 5 falls through into code 6, and unknown codes use default.
// The program exits with status 128.

int apply(int op, int a, int b) {
    int result = 0;
    switch (op) {
        case 1:
            result = a + b;
            break;
        case 2:
            result = a - b;
            break;
        case 3:
        case 4:
            result = a * b;
            break;
        case 5:
            a = a * 2; // no break: falls through into case 6
        case 6:
            result = a / b;
            break;
        default:
            result = -1;
    }
    return result;
}

int main() {
    int total = 0;
    for (int op = 1; op <= 7; op++) {
        total += apply(op, 12, 4);
    }
    return total; // 16 + 8 + 48 + 48 + 6 + 3 - 1 = 128
}
```

**Three-address code:**

```text
func apply:
begin_func
result = 0
if op == 1 goto L2
if op == 2 goto L3
if op == 3 goto L4
if op == 4 goto L5
if op == 5 goto L6
if op == 6 goto L7
goto L8
L2:
t1 = a + b
result = t1
goto L1
L3:
t2 = a - b
result = t2
goto L1
L4:
L5:
t3 = a * b
result = t3
goto L1
L6:
t4 = a * 2
a = t4
L7:
t5 = a / b
result = t5
goto L1
L8:
result = -1
L1:
return result
end_func

func main:
begin_func
total = 0
op = 1
L9:
t6 = op <= 7
if_false t6 goto L11
param op
param 12
param 4
t7 = call apply, 3
t8 = total + t7
total = t8
L10:
t9 = op
op = op + 1
goto L9
L11:
return total
end_func
```

<details>
<summary>LLVM IR</summary>

```llvm
; LLVM IR Generated by Custom Compiler
declare i32 @printf(i8*, ...)

define i32 @apply(i32 %op_arg, i32 %a_arg, i32 %b_arg) {
entry:
  %op.addr1 = alloca i32
  %a.addr2 = alloca i32
  %b.addr3 = alloca i32
  %result.addr4 = alloca i32
  store i32 %op_arg, i32* %op.addr1
  store i32 %a_arg, i32* %a.addr2
  store i32 %b_arg, i32* %b.addr3
  store i32 0, i32* %result.addr4
  %1 = load i32, i32* %op.addr1
  switch i32 %1, label %L8 [ i32 1, label %L2 i32 2, label %L3 i32 3, label %L4 i32 4, label %L5 i32 5, label %L6 i32 6, label %L7 ]
L2:
  %2 = load i32, i32* %a.addr2
  %3 = load i32, i32* %b.addr3
  %4 = add i32 %2, %3
  store i32 %4, i32* %result.addr4
  br label %L1
L3:
  %5 = load i32, i32* %a.addr2
  %6 = load i32, i32* %b.addr3
  %7 = sub i32 %5, %6
  store i32 %7, i32* %result.addr4
  br label %L1
L4:
  br label %L5
L5:
  %8 = load i32, i32* %a.addr2
  %9 = load i32, i32* %b.addr3
  %10 = mul i32 %8, %9
  store i32 %10, i32* %result.addr4
  br label %L1
L6:
  %11 = load i32, i32* %a.addr2
  %12 = mul i32 %11, 2
  store i32 %12, i32* %a.addr2
  br label %L7
L7:
  %13 = load i32, i32* %a.addr2
  %14 = load i32, i32* %b.addr3
  %15 = sdiv i32 %13, %14
  store i32 %15, i32* %result.addr4
  br label %L1
L8:
  store i32 -1, i32* %result.addr4
  br label %L1
L1:
  %16 = load i32, i32* %result.addr4
  ret i32 %16
}

define i32 @main() {
entry:
  %total.addr1 = alloca i32
  %op.addr2 = alloca i32
  store i32 0, i32* %total.addr1
  store i32 1, i32* %op.addr2
  br label %L9
L9:
  %1 = load i32, i32* %op.addr2
  %2 = icmp sle i32 %1, 7
  %3 = zext i1 %2 to i32
  %4 = icmp ne i32 %3, 0
  br i1 %4, label %L10, label %L12
L10:
  %5 = load i32, i32* %op.addr2
  %6 = call i32 @apply(i32 %5, i32 12, i32 4)
  %7 = load i32, i32* %total.addr1
  %8 = add i32 %7, %6
  store i32 %8, i32* %total.addr1
  br label %L11
L11:
  %9 = load i32, i32* %op.addr2
  %10 = add i32 %9, 1
  store i32 %10, i32* %op.addr2
  br label %L9
L12:
  %11 = load i32, i32* %total.addr1
  ret i32 %11
}
```

</details>

### Pointers and arrays (`public/examples/pointers.c`)

Swaps two values through pointers, passes an array to a function as a pointer, and walks it with `p++` to return a pointer to the largest element. `top - scores` is the number of elements between two pointers. The compiled program exits with status 73.

```c
// Pointers: swapping through out-parameters, walking an array with a
// pointer, and returning a pointer into it. The program exits with 73.

void swap(int *a, int *b) {
    int t = *a;
    *a = *b;
    *b = t;
}

// An array argument arrives as a pointer to its first element
int *largest(int *values, int n) {
    int *best = values;
    for (int *p = values + 1; p < values + n; p++) {
        if (*p > *best) {
            best = p;
        }
    }
    return best;
}

int main() {
    int scores[5];
    scores[0] = 12;
    scores[1] = 40;
    scores[2] = 7;
    scores[3] = 31;
    scores[4] = 3;

    int *top = largest(scores, 5);
    int position = top - scores;   // elements between the two pointers: 1

    swap(&scores[0], top);         // move the largest score to the front
    *top += 1;                     // the old first score, 12, becomes 13

    return scores[0] + scores[1] + position * 20; // 40 + 13 + 20 = 73
}
```

**Three-address code:**

```text
func swap:
begin_func
t1 = *a
t = t1
t2 = *b
*a = t2
*b = t
end_func

func largest:
begin_func
best = values
t3 = values + 1
p = t3
L1:
t4 = values + n
t5 = p < t4
if_false t5 goto L3
t6 = *p
t7 = *best
t8 = t6 > t7
if_false t8 goto L4
best = p
goto L5
L4:
L5:
L2:
t9 = p
p = p + 1
goto L1
L3:
return best
end_func

func main:
begin_func
alloc_array scores, 5
scores[0] = 12
scores[1] = 40
scores[2] = 7
scores[3] = 31
scores[4] = 3
param scores
param 5
t10 = call largest, 2
top = t10
t11 = top - scores
position = t11
t12 = &scores[0]
param t12
param top
t13 = call swap, 2
t14 = *top
t15 = t14 + 1
*top = t15
t16 = scores[0]
t17 = scores[1]
t18 = t16 + t17
t19 = position * 20
t20 = t18 + t19
return t20
end_func
```

<details>
<summary>LLVM IR</summary>

```llvm
; LLVM IR Generated by Custom Compiler
declare i32 @printf(i8*, ...)

define void @swap(i32* %a_arg, i32* %b_arg) {
entry:
  %a.addr1 = alloca i32*
  %b.addr2 = alloca i32*
  %t.addr3 = alloca i32
  store i32* %a_arg, i32** %a.addr1
  store i32* %b_arg, i32** %b.addr2
  %1 = load i32*, i32** %a.addr1
  %2 = load i32, i32* %1
  store i32 %2, i32* %t.addr3
  %3 = load i32*, i32** %a.addr1
  %4 = load i32*, i32** %b.addr2
  %5 = load i32, i32* %4
  store i32 %5, i32* %3
  %6 = load i32*, i32** %b.addr2
  %7 = load i32, i32* %t.addr3
  store i32 %7, i32* %6
  ret void
}

define i32* @largest(i32* %values_arg, i32 %n_arg) {
entry:
  %values.addr1 = alloca i32*
  %n.addr2 = alloca i32
  %best.addr3 = alloca i32*
  %p.addr4 = alloca i32*
  store i32* %values_arg, i32** %values.addr1
  store i32 %n_arg, i32* %n.addr2
  %1 = load i32*, i32** %values.addr1
  store i32* %1, i32** %best.addr3
  %2 = load i32*, i32** %values.addr1
  %3 = getelementptr i32, i32* %2, i32 1
  store i32* %3, i32** %p.addr4
  br label %L1
L1:
  %4 = load i32*, i32** %p.addr4
  %5 = load i32*, i32** %values.addr1
  %6 = load i32, i32* %n.addr2
  %7 = getelementptr i32, i32* %5, i32 %6
  %8 = icmp ult i32* %4, %7
  %9 = zext i1 %8 to i32
  %10 = icmp ne i32 %9, 0
  br i1 %10, label %L2, label %L4
L2:
  %11 = load i32*, i32** %p.addr4
  %12 = load i32, i32* %11
  %13 = load i32*, i32** %best.addr3
  %14 = load i32, i32* %13
  %15 = icmp sgt i32 %12, %14
  %16 = zext i1 %15 to i32
  %17 = icmp ne i32 %16, 0
  br i1 %17, label %L5, label %L7
L5:
  %18 = load i32*, i32** %p.addr4
  store i32* %18, i32** %best.addr3
  br label %L7
L7:
  br label %L3
L3:
  %19 = load i32*, i32** %p.addr4
  %20 = getelementptr i32, i32* %19, i32 1
  store i32* %20, i32** %p.addr4
  br label %L1
L4:
  %21 = load i32*, i32** %best.addr3
  ret i32* %21
}

define i32 @main() {
entry:
  %scores.addr1 = alloca [5 x i32]
  %top.addr2 = alloca i32*
  %position.addr3 = alloca i32
  %1 = getelementptr [5 x i32], [5 x i32]* %scores.addr1, i32 0, i32 0
  store i32 12, i32* %1
  %2 = getelementptr [5 x i32], [5 x i32]* %scores.addr1, i32 0, i32 1
  store i32 40, i32* %2
  %3 = getelementptr [5 x i32], [5 x i32]* %scores.addr1, i32 0, i32 2
  store i32 7, i32* %3
  %4 = getelementptr [5 x i32], [5 x i32]* %scores.addr1, i32 0, i32 3
  store i32 31, i32* %4
  %5 = getelementptr [5 x i32], [5 x i32]* %scores.addr1, i32 0, i32 4
  store i32 3, i32* %5
  %6 = getelementptr [5 x i32], [5 x i32]* %scores.addr1, i32 0, i32 0
  %7 = call i32* @largest(i32* %6, i32 5)
  store i32* %7, i32** %top.addr2
  %8 = load i32*, i32** %top.addr2
  %9 = getelementptr [5 x i32], [5 x i32]* %scores.addr1, i32 0, i32 0
  %10 = ptrtoint i32* %8 to i64
  %11 = ptrtoint i32* %9 to i64
  %12 = sub i64 %10, %11
  %13 = sdiv exact i64 %12, 4
  %14 = trunc i64 %13 to i32
  store i32 %14, i32* %position.addr3
  %15 = getelementptr [5 x i32], [5 x i32]* %scores.addr1, i32 0, i32 0
  %16 = load i32*, i32** %top.addr2
  call void @swap(i32* %15, i32* %16)
  %17 = load i32*, i32** %top.addr2
  %18 = load i32, i32* %17
  %19 = add i32 %18, 1
  store i32 %19, i32* %17
  %20 = getelementptr [5 x i32], [5 x i32]* %scores.addr1, i32 0, i32 0
  %21 = load i32, i32* %20
  %22 = getelementptr [5 x i32], [5 x i32]* %scores.addr1, i32 0, i32 1
  %23 = load i32, i32* %22
  %24 = add i32 %21, %23
  %25 = load i32, i32* %position.addr3
  %26 = mul i32 %25, 20
  %27 = add i32 %24, %26
  ret i32 %27
}
```

</details>

### Structs, an initializer list and a linked chain (`public/examples/structs.c`)

Fills an array of structs from one nested initializer list, links the items through `next` pointers, passes structs by value and by pointer, and walks the chain with `->`. The compiled program exits with status 112.

```c
// Structs: a small inventory of items kept in an array, a pointer to the
// most valuable one, and a linked chain built through next pointers.
// The program exits with status 112.

struct Item {
    int price;
    int quantity;
    struct Item *next;
};

int value(struct Item item) {
    return item.price * item.quantity;
}

struct Item *most_valuable(struct Item *items, int n) {
    struct Item *best = items;
    for (int i = 1; i < n; i++) {
        if (value(items[i]) > value(*best)) {
            best = &items[i];
        }
    }
    return best;
}

int main() {
    // price, quantity; each next pointer starts out null
    struct Item stock[] = {{4, 10}, {25, 2}, {9, 7}};

    // Chain the items together: 0 -> 1 -> 2
    for (int i = 0; i < 2; i++) {
        stock[i].next = &stock[i + 1];
    }
    stock[2].next = 0;

    struct Item *best = most_valuable(stock, 3);
    best->quantity++;          // restock the best seller: 9 x 8 = 72

    int total = 0;
    for (struct Item *it = &stock[0]; it != 0; it = it->next) {
        total += it->quantity;
    }
    return value(*best) + total + (best - stock) * 10; // 72 + 20 + 20 = 112
}
```

**Three-address code:**

```text
struct Item { int price, int quantity, struct Item* next }
func value:
begin_func
t1 = item.price
t2 = item.quantity
t3 = t1 * t2
return t3
end_func

func most_valuable:
begin_func
best = items
i = 1
L1:
t4 = i < n
if_false t4 goto L3
t5 = items[i]
param t5
t6 = call value, 1
t7 = *best
param t7
t8 = call value, 1
t9 = t6 > t8
if_false t9 goto L4
t10 = &items[i]
best = t10
goto L5
L4:
L5:
L2:
t11 = i
i = i + 1
goto L1
L3:
return best
end_func

func main:
begin_func
alloc_array stock, 3
clear stock
stock[0].price = 4
stock[0].quantity = 10
stock[1].price = 25
stock[1].quantity = 2
stock[2].price = 9
stock[2].quantity = 7
i = 0
L6:
t12 = i < 2
if_false t12 goto L8
t14 = i + 1
t13 = &stock[t14]
stock[i].next = t13
L7:
t15 = i
i = i + 1
goto L6
L8:
stock[2].next = 0
param stock
param 3
t16 = call most_valuable, 2
best = t16
t17 = best->quantity
best->quantity = t17 + 1
total = 0
t18 = &stock[0]
it = t18
L9:
t19 = it != 0
if_false t19 goto L11
t20 = it->quantity
t21 = total + t20
total = t21
L10:
t22 = it->next
it = t22
goto L9
L11:
t23 = *best
param t23
t24 = call value, 1
t25 = t24 + total
t26 = best - stock
t27 = t26 * 10
t28 = t25 + t27
return t28
end_func
```

<details>
<summary>LLVM IR</summary>

```llvm
; LLVM IR Generated by Custom Compiler
declare i32 @printf(i8*, ...)
%struct.Item = type { i32, i32, %struct.Item* }

define i32 @value(%struct.Item %item_arg) {
entry:
  %item.addr1 = alloca %struct.Item
  store %struct.Item %item_arg, %struct.Item* %item.addr1
  %1 = getelementptr %struct.Item, %struct.Item* %item.addr1, i32 0, i32 0
  %2 = load i32, i32* %1
  %3 = getelementptr %struct.Item, %struct.Item* %item.addr1, i32 0, i32 1
  %4 = load i32, i32* %3
  %5 = mul i32 %2, %4
  ret i32 %5
}

define %struct.Item* @most_valuable(%struct.Item* %items_arg, i32 %n_arg) {
entry:
  %items.addr1 = alloca %struct.Item*
  %n.addr2 = alloca i32
  %best.addr3 = alloca %struct.Item*
  %i.addr4 = alloca i32
  store %struct.Item* %items_arg, %struct.Item** %items.addr1
  store i32 %n_arg, i32* %n.addr2
  %1 = load %struct.Item*, %struct.Item** %items.addr1
  store %struct.Item* %1, %struct.Item** %best.addr3
  store i32 1, i32* %i.addr4
  br label %L1
L1:
  %2 = load i32, i32* %i.addr4
  %3 = load i32, i32* %n.addr2
  %4 = icmp slt i32 %2, %3
  %5 = zext i1 %4 to i32
  %6 = icmp ne i32 %5, 0
  br i1 %6, label %L2, label %L4
L2:
  %7 = load i32, i32* %i.addr4
  %8 = load %struct.Item*, %struct.Item** %items.addr1
  %9 = getelementptr %struct.Item, %struct.Item* %8, i32 %7
  %10 = load %struct.Item, %struct.Item* %9
  %11 = call i32 @value(%struct.Item %10)
  %12 = load %struct.Item*, %struct.Item** %best.addr3
  %13 = load %struct.Item, %struct.Item* %12
  %14 = call i32 @value(%struct.Item %13)
  %15 = icmp sgt i32 %11, %14
  %16 = zext i1 %15 to i32
  %17 = icmp ne i32 %16, 0
  br i1 %17, label %L5, label %L7
L5:
  %18 = load i32, i32* %i.addr4
  %19 = load %struct.Item*, %struct.Item** %items.addr1
  %20 = getelementptr %struct.Item, %struct.Item* %19, i32 %18
  store %struct.Item* %20, %struct.Item** %best.addr3
  br label %L7
L7:
  br label %L3
L3:
  %21 = load i32, i32* %i.addr4
  %22 = add i32 %21, 1
  store i32 %22, i32* %i.addr4
  br label %L1
L4:
  %23 = load %struct.Item*, %struct.Item** %best.addr3
  ret %struct.Item* %23
}

define i32 @main() {
entry:
  %stock.addr1 = alloca [3 x %struct.Item]
  %i.addr2 = alloca i32
  %best.addr3 = alloca %struct.Item*
  %total.addr4 = alloca i32
  %it.addr5 = alloca %struct.Item*
  store [3 x %struct.Item] zeroinitializer, [3 x %struct.Item]* %stock.addr1
  %1 = getelementptr [3 x %struct.Item], [3 x %struct.Item]* %stock.addr1, i32 0, i32 0
  %2 = getelementptr %struct.Item, %struct.Item* %1, i32 0, i32 0
  store i32 4, i32* %2
  %3 = getelementptr %struct.Item, %struct.Item* %1, i32 0, i32 1
  store i32 10, i32* %3
  %4 = getelementptr [3 x %struct.Item], [3 x %struct.Item]* %stock.addr1, i32 0, i32 1
  %5 = getelementptr %struct.Item, %struct.Item* %4, i32 0, i32 0
  store i32 25, i32* %5
  %6 = getelementptr %struct.Item, %struct.Item* %4, i32 0, i32 1
  store i32 2, i32* %6
  %7 = getelementptr [3 x %struct.Item], [3 x %struct.Item]* %stock.addr1, i32 0, i32 2
  %8 = getelementptr %struct.Item, %struct.Item* %7, i32 0, i32 0
  store i32 9, i32* %8
  %9 = getelementptr %struct.Item, %struct.Item* %7, i32 0, i32 1
  store i32 7, i32* %9
  store i32 0, i32* %i.addr2
  br label %L8
L8:
  %10 = load i32, i32* %i.addr2
  %11 = icmp slt i32 %10, 2
  %12 = zext i1 %11 to i32
  %13 = icmp ne i32 %12, 0
  br i1 %13, label %L9, label %L11
L9:
  %14 = load i32, i32* %i.addr2
  %15 = getelementptr [3 x %struct.Item], [3 x %struct.Item]* %stock.addr1, i32 0, i32 %14
  %16 = getelementptr %struct.Item, %struct.Item* %15, i32 0, i32 2
  %17 = load i32, i32* %i.addr2
  %18 = add i32 %17, 1
  %19 = getelementptr [3 x %struct.Item], [3 x %struct.Item]* %stock.addr1, i32 0, i32 %18
  store %struct.Item* %19, %struct.Item** %16
  br label %L10
L10:
  %20 = load i32, i32* %i.addr2
  %21 = add i32 %20, 1
  store i32 %21, i32* %i.addr2
  br label %L8
L11:
  %22 = getelementptr [3 x %struct.Item], [3 x %struct.Item]* %stock.addr1, i32 0, i32 2
  %23 = getelementptr %struct.Item, %struct.Item* %22, i32 0, i32 2
  store %struct.Item* null, %struct.Item** %23
  %24 = getelementptr [3 x %struct.Item], [3 x %struct.Item]* %stock.addr1, i32 0, i32 0
  %25 = call %struct.Item* @most_valuable(%struct.Item* %24, i32 3)
  store %struct.Item* %25, %struct.Item** %best.addr3
  %26 = load %struct.Item*, %struct.Item** %best.addr3
  %27 = getelementptr %struct.Item, %struct.Item* %26, i32 0, i32 1
  %28 = load i32, i32* %27
  %29 = add i32 %28, 1
  store i32 %29, i32* %27
  store i32 0, i32* %total.addr4
  %30 = getelementptr [3 x %struct.Item], [3 x %struct.Item]* %stock.addr1, i32 0, i32 0
  store %struct.Item* %30, %struct.Item** %it.addr5
  br label %L12
L12:
  %31 = load %struct.Item*, %struct.Item** %it.addr5
  %32 = icmp ne %struct.Item* %31, null
  %33 = zext i1 %32 to i32
  %34 = icmp ne i32 %33, 0
  br i1 %34, label %L13, label %L15
L13:
  %35 = load %struct.Item*, %struct.Item** %it.addr5
  %36 = getelementptr %struct.Item, %struct.Item* %35, i32 0, i32 1
  %37 = load i32, i32* %36
  %38 = load i32, i32* %total.addr4
  %39 = add i32 %38, %37
  store i32 %39, i32* %total.addr4
  br label %L14
L14:
  %40 = load %struct.Item*, %struct.Item** %it.addr5
  %41 = getelementptr %struct.Item, %struct.Item* %40, i32 0, i32 2
  %42 = load %struct.Item*, %struct.Item** %41
  store %struct.Item* %42, %struct.Item** %it.addr5
  br label %L12
L15:
  %43 = load %struct.Item*, %struct.Item** %best.addr3
  %44 = load %struct.Item, %struct.Item* %43
  %45 = call i32 @value(%struct.Item %44)
  %46 = load i32, i32* %total.addr4
  %47 = add i32 %45, %46
  %48 = load %struct.Item*, %struct.Item** %best.addr3
  %49 = getelementptr [3 x %struct.Item], [3 x %struct.Item]* %stock.addr1, i32 0, i32 0
  %50 = ptrtoint %struct.Item* %48 to i64
  %51 = ptrtoint %struct.Item* %49 to i64
  %52 = sub i64 %50, %51
  %53 = sdiv exact i64 %52, ptrtoint (%struct.Item* getelementptr (%struct.Item, %struct.Item* null, i32 1) to i64)
  %54 = trunc i64 %53 to i32
  %55 = mul i32 %54, 10
  %56 = add i32 %47, %55
  ret i32 %56
}
```

</details>
