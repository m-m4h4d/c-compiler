int main() {
    int i = 5;
    int a = i++;
    int b = ++i;
    int c = i--;
    int d = --i;
    float f = 1.5;
    f++;
    ++f;
    double g = 2.0;
    g--;
    return a + b * 10 + c * 100 + d * 1000 + i * 10000 + f + g - 50000;
}
