// Pointers: address-of, dereference, arithmetic, arrays and functions
int g = 5;
int table[4];
int *global_ptr = 0;

void swap(int *x, int *y) {
    int t = *x;
    *x = *y;
    *y = t;
}

// An array parameter is a pointer, whichever way it is written
int sum(int values[], int n) {
    int s = 0;
    for (int i = 0; i < n; i++) {
        s += values[i];
    }
    return s;
}

int sum_by_pointer(int *start, int *end) {
    int s = 0;
    while (start < end) {
        s += *start;
        start++;
    }
    return s;
}

int *largest(int *values, int n) {
    int *best = values;
    for (int *p = values + 1; p < values + n; p++) {
        if (*p > *best) {
            best = p;
        }
    }
    return best;
}

void fill(double *out, int n, double step) {
    for (int i = 0; i < n; i++) {
        *(out + i) = i * step;
    }
}

int main() {
    int r = 0;

    // Address-of and dereference, reading and writing
    int x = 3;
    int *px = &x;
    *px = *px + 4;   // x = 7
    *px += 1;        // x = 8
    r += x;

    // Pointers as out-parameters
    int a = 1;
    int b = 2;
    swap(&a, &b);
    r += a * 10 + b; // 21

    // Arrays decay to pointers; indexing and arithmetic agree
    int v[5];
    for (int i = 0; i < 5; i++) {
        v[i] = (i + 1) * (i + 1); // 1 4 9 16 25
    }
    int *p = v;
    r += p[2] + *(p + 3) + *(v + 1);       // 9 + 16 + 4
    r += sum(v, 5) + sum_by_pointer(v, v + 3); // 55 + 14

    // Pointer difference and comparison
    int *third = &v[2];
    int *end = v + 5;
    r += (end - third) * 100;               // 3 elements apart
    r += (third > p) + (third == &v[2]) * 2 + (p != third) * 4;

    // A function returning a pointer into the array
    int *big = largest(v, 5);
    r += big - v;                           // index 4
    *big = 0;
    r += v[4];                              // now 0

    // Walking with ++ and --
    int *walk = &v[4];
    walk--;
    walk--;
    r += *walk;                             // v[2] = 9

    // Pointer to pointer
    int **pp = &px;
    **pp = 40;
    r += x;                                 // 40
    *pp = &g;
    r += *px;                               // g = 5

    // Null pointers
    int *nothing = 0;
    if (!nothing) {
        r += 1;
    }
    if (global_ptr == 0 && nothing == global_ptr) {
        r += 2;
    }
    global_ptr = table;
    global_ptr[3] = 6;
    r += table[3];

    // Pointers to double, and an array of pointers
    double samples[4];
    fill(samples, 4, 0.5);
    double *last = &samples[3];
    r += *last * 10;                        // 15
    int *picks[2];
    picks[0] = &a;
    picks[1] = &b;
    *picks[1] += 100;
    r += b;                                 // 101

    return r % 256;
}
