#include "bb.h"
#include <string.h>

#ifndef BD_SIZE
#define BD_SIZE 0x4000
#endif

#ifndef BD_BLOCK_SIZE
#define BD_BLOCK_SIZE 512
#endif

// RAM-backed block device
uint8_t bd[BD_SIZE];

void bench_start(void);
void bench_stop(void);

uint32_t bd_block_count(void) {
    return BD_SIZE / BD_BLOCK_SIZE;
}

uint32_t bd_block_size(void) {
    return BD_BLOCK_SIZE;
}

int bd_read(uint32_t block, uint32_t off, void *buffer, size_t size) {
    bench_stop();
    if (block*BD_BLOCK_SIZE + off + size > BD_SIZE) {
        bench_start();
        return -EINVAL;
    }

    memcpy(buffer, &bd[block*BD_BLOCK_SIZE + off], size);
    bench_start();
    return 0;
}

int bd_prog(uint32_t block, uint32_t off, const void *buffer, size_t size) {
    bench_stop();
    if (block*BD_BLOCK_SIZE + off + size > BD_SIZE) {
        bench_start();
        return -EINVAL;
    }

    memcpy(&bd[block*BD_BLOCK_SIZE + off], buffer, size);
    bench_start();
    return 0;
}

int bd_erase(uint32_t block) {
    // noop
    return 0;
}

int bd_sync(void) {
    // noop
    return 0;
}

int bd_eraseall(void) {
    bench_stop();
    memset(bd, 0, BD_SIZE);
    bench_start();
    return 0;
}
