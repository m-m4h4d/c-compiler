// Structs: a small inventory of items kept in an array, a pointer to the
// most valuable one, and a linked chain built through next pointers.
// The program exits with status 112.

struct Item {
    int price;
    int quantity;
    struct Item *next;
};

int value(struct Item item) {
    return item.price * item.quantity;
}

struct Item *most_valuable(struct Item *items, int n) {
    struct Item *best = items;
    for (int i = 1; i < n; i++) {
        if (value(items[i]) > value(*best)) {
            best = &items[i];
        }
    }
    return best;
}

int main() {
    // price, quantity; each next pointer starts out null
    struct Item stock[] = {{4, 10}, {25, 2}, {9, 7}};

    // Chain the items together: 0 -> 1 -> 2
    for (int i = 0; i < 2; i++) {
        stock[i].next = &stock[i + 1];
    }
    stock[2].next = 0;

    struct Item *best = most_valuable(stock, 3);
    best->quantity++;          // restock the best seller: 9 x 8 = 72

    int total = 0;
    for (struct Item *it = &stock[0]; it != 0; it = it->next) {
        total += it->quantity;
    }
    return value(*best) + total + (best - stock) * 10; // 72 + 20 + 20 = 112
}
