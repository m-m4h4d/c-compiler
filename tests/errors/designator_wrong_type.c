struct Point {
    int x;
    int y;
};

int main() {
    struct Point p = {.x = 1.5, .y = &p}; // error
    return 0;
}
