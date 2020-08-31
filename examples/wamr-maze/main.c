#include <stdio.h>
#include <string.h>
#include <assert.h>
#include <nrfx_uarte.h>
#include <nrfx_clock.h>
#include <nrfx_timer.h>
#include "bb.h"

void bench_start(void);
void bench_stop(void);

// uart hooks for nrfx
nrfx_uarte_t uart = {
    .p_reg = NRF_UARTE0,
    .drv_inst_idx = NRFX_UARTE0_INST_IDX,
};
const nrfx_uarte_config_t uart_config = {
    .pseltxd = 6,
    .pselrxd = 8,
    .pselcts = NRF_UARTE_PSEL_DISCONNECTED,
    .pselrts = NRF_UARTE_PSEL_DISCONNECTED,
    .p_context = NULL,
    .baudrate = NRF_UARTE_BAUDRATE_115200,
    .interrupt_priority = NRFX_UARTE_DEFAULT_CONFIG_IRQ_PRIORITY,
    .hal_cfg = {
        .hwfc = NRF_UARTE_HWFC_DISABLED,
        .parity = NRF_UARTE_PARITY_EXCLUDED,
        NRFX_UARTE_DEFAULT_EXTENDED_STOP_CONFIG
        NRFX_UARTE_DEFAULT_EXTENDED_PARITYTYPE_CONFIG
    }
};

// stdout hook
ssize_t __box_write(int32_t handle, const void *p, size_t size) {
    bench_stop();

    // stdout or stderr only
    assert(handle == 1 || handle == 2);
    const char *buffer = p;

    int i = 0;
    while (true) {
        char *nl = memchr(&buffer[i], '\n', size-i);
        int span = nl ? nl-&buffer[i] : size-i;
        if (span == 0) {
            // pass
        } else if ((uint32_t)buffer < 0x2000000) {
            // special case for flash
            for (int j = 0; j < span; j++) {
                char c = buffer[i+j];
                nrfx_err_t err = nrfx_uarte_tx(&uart, (uint8_t*)&c, 1);
                assert(err == NRFX_SUCCESS);
                (void)err;
            }
        } else {
            nrfx_err_t err = nrfx_uarte_tx(&uart, (uint8_t*)&buffer[i], span);
            assert(err == NRFX_SUCCESS);
            (void)err;
        }
        i += span;

        if (i >= size) {
            bench_start();
            return size;
        }

        char r[2] = "\r\n";
        nrfx_err_t err = nrfx_uarte_tx(&uart, (uint8_t*)r, sizeof(r));
        assert(err == NRFX_SUCCESS);
        (void)err;
        i += 1;
    }
}


// timer hooks for nrfx
nrfx_timer_t timer0 = {
    .p_reg = NRF_TIMER0,
    .instance_id = NRFX_TIMER0_INST_IDX,
    .cc_channel_count = 4,
};
const nrfx_timer_config_t timer0_config = {
    .frequency = NRF_TIMER_FREQ_1MHz,
    .mode = NRF_TIMER_MODE_TIMER,
    .bit_width = NRF_TIMER_BIT_WIDTH_32,
    .interrupt_priority = NRFX_TIMER_DEFAULT_CONFIG_IRQ_PRIORITY,
    .p_context = NULL,
};

// timing things
void clock_handler(nrfx_clock_evt_type_t event) {
}

uint64_t timer_hi = 0;
void timer0_handler(nrf_timer_event_t event, void *p) {
    timer_hi += 1000000;
}

uint64_t timer_getns(void) {
    return timer_hi + nrfx_timer_capture(&timer0, NRF_TIMER_CC_CHANNEL1);
}

// measurement for benchmarking
uint64_t bench_value = 0;
int bench_startedyet = 0;
void bench_start(void) {
    bench_startedyet += 1;
    if (bench_startedyet > 0) {
        bench_value -= timer_getns();
    }
}

void bench_stop(void) {
    if (bench_startedyet > 0) {
        bench_value += timer_getns();
    }
    bench_startedyet -= 1;
}


// pseudo-random numbers using xorshift32
uint32_t xorshift32_state = 42;
uint32_t random_get(void) {
    uint32_t x = xorshift32_state;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    xorshift32_state = x;
    return x;
}


// maze access
#define MAZE_WIDTH_MAX (160-1)
#define MAZE_HEIGHT_MAX (160-1)
uint8_t maze[MAZE_WIDTH_MAX * MAZE_HEIGHT_MAX];
size_t maze_width;
size_t maze_height;

int maze_init(size_t width, size_t height) {
    bench_stop();
    maze_width = width;
    maze_height = height;
    memset(maze, 1, maze_width*maze_height);
    bench_start();
    return 0;
}

size_t maze_getwidth(void) {
    return maze_width;
}

size_t maze_getheight(void) {
    return maze_height;
}

int32_t maze_get(size_t x, size_t y) {
    bench_stop();
    if (x >= maze_width || y >= maze_height) {
        bench_start();
        return -EDOM;
    }

    bench_start();
    return maze[x + y*maze_width];
}

int maze_set(size_t x, size_t y, uint8_t v) {
    bench_stop();
    if (x >= maze_width || y >= maze_height) {
        bench_start();
        return -EDOM;
    }

    maze[x + y*maze_width] = v;
    bench_start();
    return 0;
}

int maze_getall(void *buffer, size_t size) {
    bench_stop();
    if (size != maze_width * maze_height) {
        bench_start();
        return -EDOM;
    }

    memcpy(buffer, maze, size);
    bench_start();
    return 0;
}

int maze_setall(const void *buffer, size_t size) {
    bench_stop();
    if (size != maze_width * maze_height) {
        bench_start();
        return -EDOM;
    }

    memcpy(maze, buffer, size);
    bench_start();
    return 0;
}

void maze_print(void) {
    bench_stop();
    for (int y = 0; y < maze_height; y += 2) {
        for (int x = 0; x < maze_width; x++) {
            uint8_t v1 = maze[x + (y+0)*maze_width];
            uint8_t v2 = (y+1 < maze_height) ? maze[x + (y+1)*maze_width] : 0;
            printf("%c",
                    (v1 > 1 || v2 > 1) ? 'x'  :
                    (v1 && v2)         ? ':'  :
                    v1                 ? '\'' :
                    v2                 ? '.'  : ' ');
        }
        printf("\n");
    }
    bench_start();
}

void maze_test(size_t width, size_t height) {
    maze_init(width, height);

    printf("generating maze (%dx%d)...\n", width, height);
    int err = maze_generate_prim(1, 1);
    printf("maze_generate_prim -> %d\n", err);
    maze_print();

    printf("reducing maze...\n");
    err = maze_reduce(4);
    printf("maze_reduce -> %d\n", err);
    maze_print();

    printf("eroding maze...\n");
    err = maze_erode(1);
    printf("maze_erode -> %d\n", err);
    maze_print();

    printf("eroding maze...\n");
    err = maze_erode(2);
    printf("maze_erode -> %d\n", err);
    maze_print();

    printf("reducing maze...\n");
    err = maze_reduce(4);
    printf("maze_reduce -> %d\n", err);
    maze_print();

    size_t *tempx = __box_mazebuilder_push(sizeof(size_t));
    size_t *tempy = __box_mazebuilder_push(sizeof(size_t));

    err = maze_findstart(tempx, tempy);
    size_t startx = *tempx;
    size_t starty = *tempy;
    printf("maze_findstart -> %d (%d, %d)\n", err, startx, starty);

    err = maze_findend(tempx, tempy);
    size_t endx = *tempx;
    size_t endy = *tempy;
    printf("maze_findend -> %d (%d, %d)\n", err, endx, endy);

    __box_mazebuilder_pop(sizeof(size_t));
    __box_mazebuilder_pop(sizeof(size_t));

    printf("solving maze...\n");
    err = maze_solve(startx, starty, endx, endy);
    printf("maze_solve -> %d\n", err);
    maze_print();
}


// entry point
void main(void) {
    nrfx_err_t nerr;
    // setup LCLK
    nerr = nrfx_clock_init(clock_handler);
    (void)nerr; assert(nerr == NRFX_SUCCESS);
    nrfx_clock_start(NRF_CLOCK_DOMAIN_LFCLK);

    // setup UART
    nerr = nrfx_uarte_init(&uart, &uart_config, NULL);
    (void)nerr; assert(nerr == NRFX_SUCCESS);

    // setup TIMER0
    nerr = nrfx_timer_init(&timer0, &timer0_config, &timer0_handler);
    (void)nerr; assert(nerr == NRFX_SUCCESS);
    nrfx_timer_extended_compare(&timer0, NRF_TIMER_CC_CHANNEL0,
        nrfx_timer_ms_to_ticks(&timer0, 1000),
        NRF_TIMER_SHORT_COMPARE0_CLEAR_MASK, true);
    nrfx_timer_enable(&timer0);

    printf("hi from nrf52840!\n");
    bench_start();

    maze_test(20-1, 20-1);
    maze_test(40-1, 40-1);
    maze_test(80-1, 80-1);
    //maze_test(120-1, 120-1);
    maze_test(160-1, 160-1);

    bench_stop();
    printf("done\n");

    // log cycles
    if (bench_value >> 32) {
        printf("sys: %u*(2^32) + %u ns\n",
            (uint32_t)(bench_value >> 32), (uint32_t)bench_value);
    } else {
        printf("sys: %u ns\n", (uint32_t)bench_value);
    }

    // clear maze to remove it from our measurement (note
    // there's still copies of the maze in our boxes, but
    // we will include these)
    memset(maze, 0, sizeof(maze));

    // log ram usage, and then mark it for the next run
    uint32_t *ram_start = (uint32_t*)0x20000000;
    uint32_t *ram_end   = (uint32_t*)0x20040000;

    uint32_t ram_usage = 0;
    for (uint32_t *p = ram_start; p < ram_end; p++) {
        if (*p != 0x00000000) {
            ram_usage += 4;
        }
    }
    printf("sys: %u bytes ram\n", ram_usage);

    for (uint32_t *p = ram_start; p < ram_end; p++) {
        *p = 0x00000000;
    }
}
