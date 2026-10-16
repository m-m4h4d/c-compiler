struct Point {
    int x;
};

int main() {
    struct Point p = {.z = 1}; // error
    return 0;
}
