// A tour of the language: functions, loops, arrays and constant folding.
// The finished program exits with status 165.

int arithmetic() {
    int a = 10;
    int b = 5 + 3; // folded to 8 at compile time
    return a * b;
}

int loops() {
    int sum = 0;
    int i = 0;
    while (i < 10) {
        sum = sum + i;
        i++;
    }
    for (int j = 0; j < 5; j++) {
        sum = sum + j;
    }
    if (0) {
        sum = 0; // dead code: removed by the optimizer
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
