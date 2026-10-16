int history[8];
int count;

void record(int value) {
    if (value < 0) {
        return;
    }
    history[count] = value;
    count++;
}

int main(void) {
    record(3);
    record(0 - 1);
    record(4);
    record(5);
    return count * 100 + history[0] + history[1] + history[2];
}
