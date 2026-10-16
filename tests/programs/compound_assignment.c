// Compound assignment: +=, -=, *=, /= and %= on variables and array elements
int calls;

int next_index() {
    calls++;
    return 1;
}

int main() {
    int x = 10;
    x += 5;    // 15
    x -= 3;    // 12
    x *= 4;    // 48
    x /= 5;    // 9
    x %= 4;    // 1
    int r = x;

    // C's division and remainder truncate toward zero
    int n = -7;
    n /= 2;    // -3
    int m = -7;
    m %= 3;    // -1
    r = r + (n + 10) * 2 + (m + 10) * 3;

    // The result is converted back to the variable's type
    int i = 3;
    i *= 2.5;  // 7.5 truncates to 7
    float f = 1.5;
    f += 2;    // 3.5
    f *= f;    // 12.25
    r = r + i + f;

    // Array elements, with the index evaluated only once
    int a[4];
    for (int k = 0; k < 4; k += 1) {
        a[k] = k * 10;
    }
    int j = 0;
    a[j++] += 5;            // a[0] = 5, j = 1
    a[next_index()] *= 3;   // a[1] = 30, one call
    a[3] -= a[2];           // 30 - 20 = 10
    r = r + a[0] + a[1] + a[3] + j * 100 + calls * 1000;

    // Assignments chain right to left and yield the stored value
    int p = 1;
    int q = 2;
    p += q += 3;  // q = 5, p = 6
    r = r + p * q;

    // Counting by steps in a for loop
    int steps = 0;
    for (int s = 0; s < 20; s += 4) {
        steps++;
    }
    return (r + steps) % 256;
}
