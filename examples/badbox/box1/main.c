#include "bb.h"
#include <stdio.h>
#include <assert.h>

int32_t x = 123;

int32_t box1_add2(int32_t a, int32_t b) {
    return a + b;
}

int box1_hello(void) {
    printf("box1 says hello!\n");
    return 0;
}

int box1_badassert(void) {
    assert(x == 0);
    return 0;
}

int box1_badread(void) {
    return *(volatile uint32_t*)0x20000000;
}

int box1_badwrite(void) {
    *(volatile uint32_t*)0x20000000 = 123;
    return 0;
}

int box1_overflow(void) {
    box1_overflow();

    // make sure this isn't tail recursive
    return 0;
}
