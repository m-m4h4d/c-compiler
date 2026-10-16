// break and continue in every kind of loop
int main() {
    int r = 0;

    // continue in a for loop must still run the increment
    for (int i = 0; i < 10; i++) {
        if (i % 2 == 0) {
            continue;
        }
        r = r + i; // 1 + 3 + 5 + 7 + 9 = 25
    }

    // break leaves only the innermost loop
    int pairs = 0;
    for (int a = 0; a < 5; a++) {
        for (int b = 0; b < 5; b++) {
            if (b > a) {
                break;
            }
            pairs++;
        }
    }
    r = r + pairs; // 15

    // break is the only way out of these loops
    int n = 0;
    while (1) {
        n++;
        if (n == 6) {
            break;
        }
    }
    for (;;) {
        n = n + 10;
        if (n > 40) {
            break;
        }
        continue;
        n = 1000; // never runs
    }
    r = r + n; // 46

    // continue in a while loop goes back to the condition
    int k = 0;
    int odd = 0;
    while (k < 7) {
        k++;
        if (k % 2 == 0) {
            continue;
        }
        odd = odd + k;
    }
    return r + odd; // 25 + 15 + 46 + 16 = 102
}
