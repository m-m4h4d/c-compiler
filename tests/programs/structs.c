// Structs: fields, nesting, arrays, pointers, copying, passing and returning
struct Point {
    int x;
    int y;
};

struct Rect {
    struct Point corner;   // a nested struct
    int width;
    int height;
};

struct Stats {
    int counts[4];         // an array field
    double total;
    int n;
};

struct Node {
    int value;
    struct Node *next;     // a pointer to the struct being defined
};

struct Point origin;       // a global struct starts zeroed

int area(struct Rect r) {
    return r.width * r.height;
}

// A struct passed by value is a copy: changing it doesn't change the caller's
int moved_x(struct Point p) {
    p.x += 100;
    return p.x;
}

void move(struct Point *p, int dx, int dy) {
    p->x += dx;
    p->y += dy;
}

struct Point make_point(int x, int y) {
    struct Point p;
    p.x = x;
    p.y = y;
    return p;
}

int list_sum(struct Node *head) {
    int s = 0;
    while (head != 0) {
        s += head->value;
        head = head->next;
    }
    return s;
}

int main() {
    int r = 0;

    // Fields, reading and writing
    struct Point a;
    a.x = 3;
    a.y = 4;
    r += a.x * 10 + a.y;                     // 34

    // Copying a whole struct
    struct Point b = a;
    b.x = 9;
    r += a.x + b.x;                          // 3 + 9: a is unchanged

    // Pass by value, by pointer, and return by value
    r += moved_x(a) + a.x;                   // 103 + 3
    move(&a, 1, 2);
    r += a.x + a.y;                          // 4 + 6
    struct Point c = make_point(7, 8);
    r += c.x + c.y + make_point(1, 2).y;     // 7 + 8 + 2

    // Nested structs
    struct Rect box;
    box.corner = make_point(5, 6);
    box.corner.y += 1;
    box.width = 3;
    box.height = 2;
    r += box.corner.x + box.corner.y + area(box);   // 5 + 7 + 6

    // Array fields, ++ on members and elements
    struct Stats s;
    s.n = 0;
    s.total = 0.0;
    for (int i = 0; i < 4; i++) {
        s.counts[i] = i * i;
        s.total += s.counts[i] * 0.5;
        s.n++;
    }
    s.counts[3]++;
    ++s.counts[0];
    int *first = s.counts;                   // an array field decays to a pointer
    r += s.counts[3] + first[0] + s.n + s.total;    // 10 + 1 + 4 + 7

    // Arrays of structs and pointers into them
    struct Point pts[3];
    for (int i = 0; i < 3; i++) {
        pts[i].x = i;
        pts[i].y = i * 10;
    }
    struct Point *pp = &pts[1];
    pp->y += 5;
    (*pp).x *= 4;
    pp++;
    r += pts[1].x + pts[1].y + pp->y + (pp - pts);  // 4 + 15 + 20 + 2
    int *py = &pts[0].y;
    *py = 50;
    r += pts[0].y;                           // 50

    // A linked list through next pointers
    struct Node nodes[3];
    for (int i = 0; i < 3; i++) {
        nodes[i].value = (i + 1) * 100;
        nodes[i].next = 0;
    }
    nodes[0].next = &nodes[1];
    nodes[1].next = &nodes[2];
    r += list_sum(&nodes[0]) / 100;          // 6
    r += nodes[0].next->next->value / 100;   // 3

    // Globals start zeroed
    r += origin.x + origin.y;
    origin.x = 2;
    r += origin.x;

    return r % 256;
}
