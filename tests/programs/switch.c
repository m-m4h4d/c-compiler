// switch: matching, default, fall-through, break and continue
int classify(int n) {
    switch (n) {
        case 0:
            return 100;
        case 1:
        case 2:     // several labels share one body
            return 200;
        case -1:    // negative and folded constants are allowed
            return 300;
        case 2 * 5:
            return 400;
        default:
            return 500;
    }
}

int fall_through(int n) {
    int r = 0;
    switch (n) {
        case 1:
            r += 1;   // no break: runs on into case 2
        case 2:
            r += 10;
            break;
        case 3:
            r += 100;
    }
    return r;
}

int no_default(int n) {
    int r = 7;
    switch (n) {
        case 5:
            r = 50;
            break;
    }
    return r;   // unchanged when nothing matches
}

int default_first(int n) {
    switch (n) {
        default:
            return 1;
        case 9:
            return 9;
    }
}

int main() {
    int r = 0;
    r += classify(0) + classify(1) + classify(2) + classify(-1) + classify(10) + classify(42);
    r += fall_through(1) + fall_through(2) + fall_through(3) + fall_through(4);
    r += no_default(5) + no_default(6);
    r += default_first(9) + default_first(3);

    // Inside a loop, break leaves the switch and continue goes to the loop
    int evens = 0;
    int threes = 0;
    for (int i = 0; i < 12; i++) {
        switch (i % 3) {
            case 0:
                threes++;
                break;
            case 1:
                continue;
        }
        if (i % 2 == 0) {
            evens++;
        }
    }
    r += evens * 7 + threes * 11;

    // The body is one scope: a declaration in one case is visible in the next
    int k = 1;
    switch (k) {
        case 0: {
            r += 1000;
            break;
        }
        case 1:
            int bonus = 3;
            r += bonus;
        case 2:
            r += k;
    }

    // A switch on a computed value, nested in a while loop
    int day = 0;
    int weekend = 0;
    while (day < 7) {
        switch (day) {
            case 0:
            case 6:
                weekend++;
                break;
            default:
                break;
        }
        day++;
    }
    return (r + weekend) % 256;
}
