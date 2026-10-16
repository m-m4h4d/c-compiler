// Designated initializers: .field and [index], in any order
struct Point {
    int x;
    int y;
};

struct Rect {
    struct Point corner;
    int width;
    int height;
};

struct Config {
    int flags[4];
    double scale;
    int level;
};

struct Point g_p = {.y = 7};                         // x is 0
int g_table[6] = {[5] = 50, [1] = 10};
struct Rect g_box = {.height = 3, .corner.y = 2};
int g_sized[] = {[3] = 9};                           // size 4, from the highest index

int main() {
    int r = 0;

    // Any order; members left out are zero
    struct Point p = {.y = 4, .x = 3};
    struct Point only_y = {.y = 8};
    r += p.x * 10 + p.y + only_y.x + only_y.y;                        // 34 + 8

    // Nested designators, and a braced value for a whole member
    struct Rect a = {.corner.x = 1, .height = 5};
    struct Rect b = {.corner = {6, 7}, .width = 2};
    r += a.corner.x + a.corner.y + a.width + a.height;                // 1 + 0 + 0 + 5
    r += b.corner.x + b.corner.y + b.width + b.height;                // 6 + 7 + 2 + 0

    // After a designator, positional values carry on from the next member
    struct Rect c = {.corner.x = 1, 2, 3};                            // corner.y = 2, width = 3
    int d[6] = {[2] = 20, 30, 40};                                    // d[3] = 30, d[4] = 40
    int e[5] = {1, [3] = 4, 5};                                       // e[4] = 5
    r += c.corner.y * 10 + c.width + d[3] + d[4] + d[5] + e[0] + e[4];

    // The highest index decides an unsized array's length
    int sized[] = {[4] = 2, [1] = 1};
    int *end = sized + 5;
    r += sized[4] + sized[1] + sized[0] + (end - sized);              // 2 + 1 + 0 + 5

    // Arrays of structs, and array fields
    struct Point pts[3] = {[2].y = 9, [0] = {.x = 4}};
    struct Config cfg = {.flags = {[3] = 1}, .level = 2, .scale = 0.5};
    struct Config flat = {.flags[1] = 6, 7};                          // flags[2] = 7
    r += pts[0].x + pts[2].y + pts[1].x + cfg.flags[3] + cfg.level + cfg.scale * 4;
    r += flat.flags[1] + flat.flags[2] + flat.flags[3];

    // A later value for the same member wins
    struct Point twice = {.x = 1, .x = 2};
    int over[3] = {[1] = 5, [1] = 6};
    r += twice.x + over[1];

    // Globals
    r += g_p.x + g_p.y + g_table[5] + g_table[1] + g_table[0];
    r += g_box.corner.y + g_box.height + g_box.width + g_sized[3];
    return r % 256;
}
