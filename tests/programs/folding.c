// Constant folding must match C's truncating division and remainder
int main() {
    int a = (0 - 7) / 2;
    int b = (0 - 7) % 2;
    int c = 7 / (0 - 2);
    int d = 7 % (0 - 2);
    int e = (0 - 9) / (0 - 4);
    int f = (0 - 9) % (0 - 4);
    int g = (2.5 < 3.0) + (1.5 == 1.5) * 2;
    double h = 1.0 / 4.0 + 7 / 2;
    int seven = 7;
    int r = 0;
    if (a == (0 - seven) / 2) { r = r + 1; }
    if (b == (0 - seven) % 2) { r = r + 2; }
    if (c == seven / (0 - 2)) { r = r + 4; }
    if (d == seven % (0 - 2)) { r = r + 8; }
    if (h == 3.25) { r = r + 16; }
    return r + (a + 10) + (b + 10) * 2 + (c + 10) * 3 + d * 4 + e * 5 + (f + 10) * 6 + g * 7;
}
