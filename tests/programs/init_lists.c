// Initializer lists for structs and arrays, local and global
struct Point {
    int x;
    int y;
};

struct Rect {
    struct Point corner;
    int width;
    int height;
};

struct Stats {
    int counts[3];
    double scale;
    int *target;
};

struct Point g_origin = {0, 0};
struct Rect g_box = {{1, 2}, 30};               // height is left out, so 0
int g_primes[] = {2, 3, 5, 7, 11};             // size 5, from the list
struct Point g_path[3] = {{1, 1}, {2, 4}};     // the third point is zero
double g_weights[4] = {0.5, 1};                // int converts to double
int g_value = {42};                            // braces around a scalar

int twice(int n) {
    return n * 2;
}

int main() {
    int r = 0;

    // Structs: in order, nested, and with members left out
    struct Point p = {3, 4};
    struct Rect box = {{5, 6}, 7, 8};
    struct Rect partial = {{9}};               // corner.y, width, height are 0
    r += p.x + p.y + box.corner.y + box.height + partial.corner.x + partial.width;

    // Brace elision: the inner struct takes values without its own braces
    struct Rect flat = {1, 2, 3, 4};
    r += flat.corner.x * 1000 + flat.corner.y * 100 + flat.width * 10 + flat.height;

    // Arrays, with an inferred size, and arrays of structs
    int a[5] = {10, 20};                       // a[2..4] are 0
    int b[] = {1, 2, 3};
    struct Point pts[] = {{1, 2}, {3, 4}, {5, 6}};
    r += a[1] + a[4] + b[2] + (pts[2].x + pts[2].y) * 3;

    // Array fields, conversions, and a pointer field
    int hits = 7;
    struct Stats s = {{4, 5}, 2, &hits};       // counts[2] is 0, scale is 2.0
    *s.target += 1;
    r += s.counts[1] + s.counts[2] + s.scale * 10 + hits;

    // Any expression in a local initializer, including a struct copy
    int base = 6;
    struct Point q = {base + 1, twice(base)};
    struct Rect copy = {q, q.x, 0};
    r += q.x + q.y + copy.corner.y + copy.width;

    // A trailing comma, and an empty list that zeroes everything
    int c[3] = {1, 2, 3,};
    struct Point zero = {};
    r += c[2] + zero.x + zero.y;

    // Initializers run each time: the array is re-zeroed on every iteration
    int total = 0;
    for (int i = 1; i <= 3; i++) {
        int row[3] = {i};
        total += row[0] * 10 + row[1] + row[2];
        row[1] = 99;
    }
    r += total;

    // Globals
    r += g_origin.x + g_box.corner.y + g_box.width + g_box.height;
    r += g_primes[4] + g_path[1].y + g_path[2].x + g_weights[1] * 2 + g_value;
    return r % 256;
}
