// ++ and -- on array elements, through pointers, and on struct members
struct Counter {
    int hits;
    double level;
};

int main() {
    int a[3];
    a[0] = 5;
    a[1] = 10;
    a[2] = 20;
    int r = 0;

    r += a[0]++;      // yields 5, a[0] becomes 6
    r += ++a[1];      // a[1] becomes 11
    a[2]--;           // 19
    --a[2];           // 18
    r += a[0] + a[2];

    int x = 7;
    int *p = &x;
    (*p)++;
    ++*p;
    r += x;           // 9

    int *walk = a;
    *walk++ = 40;     // stores to a[0], then moves to a[1]
    r += *walk + a[0];  // 11 + 40

    struct Counter c;
    c.hits = 0;
    c.level = 1.5;
    c.hits++;
    ++c.hits;
    c.level++;
    struct Counter *cp = &c;
    cp->hits++;
    r += c.hits * 100 + c.level * 2;   // 300 + 5

    int i = 0;
    a[i++] += 1;      // a[0] = 41, i = 1: the index runs once
    r += a[0] + i;
    return r % 256;
}
