// do-while runs its body before checking the condition
int main() {
    int r = 0;

    // A false condition still runs the body once
    int once = 0;
    do {
        once++;
    } while (0);
    r = r + once; // 1

    // Counting up, with a body that isn't a block
    int n = 0;
    do n++; while (n < 5);
    r = r + n * 10; // 50

    // continue jumps to the condition, so the loop still ends
    int i = 0;
    int odd = 0;
    do {
        i++;
        if (i % 2 == 0) {
            continue;
        }
        odd += i;
    } while (i < 9);
    r = r + odd; // 1 + 3 + 5 + 7 + 9 = 25

    // break leaves the loop even though the condition is always true
    int k = 0;
    do {
        k += 3;
        if (k > 10) {
            break;
        }
    } while (1);
    r = r + k; // 12

    // Nested inside another loop, with a declaration in the body
    int total = 0;
    for (int row = 1; row <= 3; row++) {
        int col = 0;
        do {
            int cell = row * col;
            total += cell;
            col++;
        } while (col < row);
    }
    r = r + total; // 0 + (0+2) + (0+3+6) = 11

    // Digit sum, the classic do-while: works for 0 as well
    int value = 4096;
    int digits = 0;
    do {
        digits += value % 10;
        value /= 10;
    } while (value > 0);
    return r + digits; // 1 + 50 + 25 + 12 + 11 + 19 = 118
}
