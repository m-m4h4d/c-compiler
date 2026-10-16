int counter;
int base = 10 * 3 + 2;
int negative = -5;
float scale = 0.1;
double ratio = 1.0 / 8.0;
int truncated = 7.9;
int table[4];

void tick(void) {
    counter = counter + 1;
}

int fill() {
    int i;
    for (i = 0; i < 4; i = i + 1) {
        table[i] = i * base;
    }
    return table[3];
}

int main() {
    tick();
    tick();
    int r = fill();
    int base = 1; // shadows the global
    r = r + base + counter + negative + truncated;
    if (scale > 0.09 && scale < 0.11) { r = r + 100; }
    if (ratio == 0.125) { r = r + 50; }
    return r;
}
