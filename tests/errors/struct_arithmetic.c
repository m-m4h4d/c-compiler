struct Point {
    int x;
};

int main() {
    struct Point p;
    int n = p + 1; // error
    return n;
}
