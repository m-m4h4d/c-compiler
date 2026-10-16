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
