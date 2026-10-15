float half(float x) {
    return x / 2.0;
}

double area(double w, double h) {
    return w * h;
}

int main() {
    float f = 1.5;
    double d = 0.1;
    int n = 3;
    f = f * 2.0 + n;
    d = d + 0.2;
    int r = 0;
    if (f > 5.9) { r = r + 1; }
    if (d < 0.31) { r = r + 2; }
    if (half(9.0) == 4.5) { r = r + 4; }
    if (-f < 0.0) { r = r + 8; }
    if (!(f == 0.0)) { r = r + 16; }
    r = r + area(2.5, 4);
    return r + f;
}
