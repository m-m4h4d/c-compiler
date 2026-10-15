int sign(int x) {
    if (x > 0) {
        return 1;
    } else {
        if (x < 0) {
            return 2;
        }
    }
    return 3;
}

int first_over(int limit) {
    int i = 0;
    while (i < 100) {
        if (i * i > limit) {
            return i;
        }
        i = i + 1;
    }
    return 0;
}

int main() {
    return sign(5) + sign(0 - 5) * 10 + sign(0) * 100 + first_over(50);
}
