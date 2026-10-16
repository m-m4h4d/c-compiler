// Mixed int, float and double arithmetic with implicit conversions.

float half(float x) {
    return x / 2.0;
}

double area(double w, double h) {
    return w * h;
}

int main() {
    float f = 1.5;
    int n = 3;
    f = f * 2.0 + n;      // 6.0
    double a = area(2.5, 4); // the int 4 becomes a double
    if (half(9.0) == 4.5) {
        return a + f;     // 16.0, converted back to an int
    }
    return 0;
}
