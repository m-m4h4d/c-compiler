struct Point {
    int x;
};

int main() {
    struct Point a;
    struct Point b;
    return a == b; // error
}
