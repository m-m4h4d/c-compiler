// Mixed types that C allows: the type checker must accept all of these
double scale(double x, int factor) {
    return x * factor;   // int widens to double
}

int truncate(double x) {
    return x;            // double narrows to int on return
}

int main() {
    int i = 7;
    float f = 2.5;
    double d = 0.25;

    int from_double = d * 10 + 0.9;   // 3.4 truncates to 3
    float mixed = i / 2 + f;          // int division first: 3 + 2.5
    double wide = f * d;              // float widens to double

    int r = from_double + mixed + wide * 8;            // 3 + 5 + 5 = 13
    r += scale(1.5, 4) + truncate(9.99);              // 6 + 9
    r += (f > i) + (d < 1) * 2 + (f == 2.5) * 4;      // 0 + 2 + 4
    r += !d + !(d - 0.25) * 10 + (f && i) * 100;      // 0 + 10 + 100
    r += -f * 2;                                      // -5

    int counts[3];
    counts[i % 3] = 1;    // an int expression as the index
    counts[2] = i / 3;    // 2
    return r + counts[1] + counts[2] * 1000 % 256;    // r + 1 + 208
}
