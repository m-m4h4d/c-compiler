/* Global variables and arrays, shared between functions.
   A void function updates them. */

int count;
int history[8];

void record(int value) {
    if (value < 0) {
        return;
    }
    history[count] = value;
    count++;
}

int main(void) {
    record(3);
    record(-1);
    record(4);
    return count * 10 + history[0] + history[1];
}
