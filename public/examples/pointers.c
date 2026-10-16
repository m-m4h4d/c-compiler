// Pointers: swapping through out-parameters, walking an array with a
// pointer, and returning a pointer into it. The program exits with 73.

void swap(int *a, int *b) {
    int t = *a;
    *a = *b;
    *b = t;
}

// An array argument arrives as a pointer to its first element
int *largest(int *values, int n) {
    int *best = values;
    for (int *p = values + 1; p < values + n; p++) {
        if (*p > *best) {
            best = p;
        }
    }
    return best;
}

int main() {
    int scores[5];
    scores[0] = 12;
    scores[1] = 40;
    scores[2] = 7;
    scores[3] = 31;
    scores[4] = 3;

    int *top = largest(scores, 5);
    int position = top - scores;   // elements between the two pointers: 1

    swap(&scores[0], top);         // move the largest score to the front
    *top += 1;                     // the old first score, 12, becomes 13

    return scores[0] + scores[1] + position * 20; // 40 + 13 + 20 = 73
}
