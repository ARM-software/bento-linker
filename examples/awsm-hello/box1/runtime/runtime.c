#include "runtime.h"

// TODO: Throughout here we use `assert` for error conditions, which isn't optimal
// Instead we should use `unlikely` branches to a single trapping function (which should optimize better)

// Needed to support C++
void env___cxa_pure_virtual() { awsm_assert("env___cxa_pure_virtual" == 0); }

// Region initialization helper function
EXPORT void initialize_region(u32 offset, u32 data_count, char* data) {
    awsm_assert(memory_size >= data_count);
    awsm_assert(offset < memory_size - data_count);
//    awsm_assert(offset <= memory_size - data_count);

    // FIXME: Hack around segmented and unsegmented access
    memcpy(get_memory_ptr_for_runtime(offset, data_count), data, data_count);
}


// The below functions are for implementing WASM instructions

// ROTL and ROTR helper functions
INLINE u32 rotl_u32(u32 n, u32 c_u32) {
    // WASM requires a modulus here (usually a single bitwise op, but it means we need no assert)
    unsigned int c = c_u32 % (CHAR_BIT * sizeof(n));
    const unsigned int mask = (CHAR_BIT * sizeof(n) - 1);  // assumes width is a power of 2.

    c &= mask;
    return (n << c) | (n >> ((-c) & mask));
}

INLINE u32 rotr_u32(u32 n, u32 c_u32) {
    // WASM requires a modulus here (usually a single bitwise op, but it means we need no assert)
    unsigned int c = c_u32 % (CHAR_BIT * sizeof(n));
    const unsigned int mask = (CHAR_BIT * sizeof(n) - 1);

    c &= mask;
    return (n>>c) | (n << ((-c) & mask));
}

INLINE u64 rotl_u64(u64 n, u64 c_u64) {
    // WASM requires a modulus here (usually a single bitwise op, but it means we need no assert)
    unsigned int c = c_u64 % (CHAR_BIT * sizeof(n));
    const unsigned int mask = (CHAR_BIT * sizeof(n) - 1);  // assumes width is a power of 2.

    c &= mask;
    return (n << c) | (n >> ((-c) & mask));
}

INLINE u64 rotr_u64(u64 n, u64 c_u64) {
    // WASM requires a modulus here (usually a single bitwise op, but it means we need no assert)
    unsigned int c = c_u64 % (CHAR_BIT * sizeof(n));
    const unsigned int mask = (CHAR_BIT * sizeof(n) - 1);

    c &= mask;
    return (n >> c) | (n << ((-c) & mask));
}

// Now safe division and remainder
INLINE u32 u32_div(u32 a, u32 b) {
    awsm_assert(b);
    return a / b;
}

INLINE u32 u32_rem(u32 a, u32 b) {
    awsm_assert(b);
    return a % b;
}

INLINE i32 i32_div(i32 a, i32 b) {
    awsm_assert(b && (a != INT32_MIN || b != -1));
    return a / b;
}

INLINE i32 i32_rem(i32 a, i32 b) {
    awsm_assert(b && (a != INT32_MIN || b != -1));
    return a % b;
}

INLINE u64 u64_div(u64 a, u64 b) {
    awsm_assert(b);
    return a / b;
}

INLINE u64 u64_rem(u64 a, u64 b) {
    awsm_assert(b);
    return a % b;
}

INLINE i64 i64_div(i64 a, i64 b) {
    awsm_assert(b && (a != INT64_MIN || b != -1));
    return a / b;
}

INLINE i64 i64_rem(i64 a, i64 b) {
    awsm_assert(b && (a != INT64_MIN || b != -1));
    return a % b;
}



// float to integer conversion methods
// In C, float => int conversions always truncate
// If a int2float(int::min_value) <= float <= int2float(int::max_value), it must always be safe to truncate it
u32 u32_trunc_f32(float f) {
    awsm_assert(0 <= f && f <= (float) UINT32_MAX);
    return (u32) f;
}

i32 i32_trunc_f32(float f) {
    awsm_assert(INT32_MIN <= f && f <= (float) INT32_MAX);
    return (i32) f;
}

u32 u32_trunc_f64(double f) {
    awsm_assert(0 <= f && f <= (float) UINT32_MAX);
    return (u32) f;
}

i32 i32_trunc_f64(double f) {
    awsm_assert(INT32_MIN <= f && f <= (float) INT32_MAX );
    return (i32) f;
}

u64 u64_trunc_f32(float f) {
    awsm_assert(0 <= f && f <= (float) UINT64_MAX);
    return (u64) f;
}

i64 i64_trunc_f32(float f) {
    awsm_assert(INT64_MIN <= f && f <= (float) INT64_MAX);
    return (i64) f;
}

u64 u64_trunc_f64(double f) {
    awsm_assert(0 <= f && f <= (double) UINT64_MAX);
    return (u64) f;
}

i64 i64_trunc_f64(double f) {
    awsm_assert(INT64_MIN <= f && f <= (double) INT64_MAX);
    return (i64) f;
}

// Float => Float truncation functions
INLINE float f32_trunc_f32(float f) {
    return trunc(f);
}

INLINE float f32_min(float a, float b) {
    return a < b ? a : b;
}

INLINE float f32_max(float a, float b) {
    return a > b ? a : b;
}

INLINE float f32_floor(float a) {
    return floorf(a);
}

INLINE float f32_ceil(float a) {
    return ceil(a);
}

INLINE float f32_nearest(float a) {
    return round(a);
}

INLINE float f32_copysign(float a, float b) {
    return copysignf(a, b);
}

INLINE double f64_min(double a, double b) {
    return a < b ? a : b;
}

INLINE double f64_max(double a, double b) {
    return a > b ? a : b;
}

INLINE double f64_floor(double a) {
    return floor(a);
}

INLINE double f64_ceil(double a) {
    return ceil(a);
}

INLINE double f64_nearest(double a) {
    return round(a);
}

INLINE double f64_copysign(double a, double b) {
    return copysign(a, b);
}

// Memory related instructions
i32 instruction_memory_size() {
    return memory_size / WASM_PAGE_SIZE;
}

i32 instruction_memory_grow(i32 count) {
    i32 prev_size = instruction_memory_size();
    for (int i = 0; i < count; i++) {
        expand_memory();
    }

    return prev_size;
}


// We want to have some allocation logic
WEAK u32 wasmg___heap_base = 0;
u32 runtime_heap_base;

u32 allocate_n_bytes(u32 n) {
    u32 res = runtime_heap_base;
    runtime_heap_base += n;
    while (memory_size < runtime_heap_base) {
        expand_memory();
    }
    printf("rhb %d\n", runtime_heap_base);
    return res;
}

void* allocate_n_bytes_ptr(u32 n) {
    u32 addr = allocate_n_bytes(n);
    return get_memory_ptr_for_runtime(addr, n);
}

// FIXME: Currently the timer support stuff is disabled, pending cortex_m results
// this provides a way to add a timeout for wasm execution, and support for that
// TODO: Add a way for awsm to give us this value
//WEAK unsigned int wasm_execution_timeout_ms = 0;
//sigjmp_buf timeout_jump;
//#define JUMPING_BACK 0xBACC

// Precondition: you've already loaded timeout_jump with where we should jump after the timeout
//void handle_sigalarm(int sig) {
//    // TODO: We use siglongjmp which resets signal stuff, so perhaps this call is unnessesary
//    signal(sig, SIG_IGN);
//    siglongjmp(timeout_jump, JUMPING_BACK);
//}
//
//void schedule_timeout() {
//    signal(SIGALRM, handle_sigalarm);
//    ualarm(wasm_execution_timeout_ms * 1000, 0);
//}
//
//void cancel_timeout() {
//    ualarm(0, 0);
//}

// If we are using runtime globals, we need to populate them
WEAK void populate_globals() {}

// Code that actually runs the wasm code
IMPORT i32 wasmf_main(i32 a, i32 b);

int runtime_main(int argc, char** argv) {
    // Setup the linear memory and function table
    alloc_linear_memory();
    populate_table();

    // Setup our allocation logic
    runtime_heap_base = wasmg___heap_base;
    printf("starting rhb %d\n", runtime_heap_base);
    if (runtime_heap_base == 0) {
        runtime_heap_base = memory_size;
    }

    // Setup the global values (if needed), and populate the linear memory
    switch_out_of_runtime();
    populate_globals();
    switch_into_runtime();
    populate_memory();

    // In the case of a real timeout being compiled in, handle that
//    if (wasm_execution_timeout_ms) {
//        // Set the jumpoint to here, and save the signal mask
//        int res = sigsetjmp(timeout_jump, 1);
//        if (res != 0) {
//            assert(res == JUMPING_BACK);
//            printf("WE DECIDED TO GIVE UP\n");
//            return -JUMPING_BACK;
//        }
//        schedule_timeout();
//    }

    u32 array_offset = allocate_n_bytes(argc * sizeof(i32));
    u32* array_ptr = get_memory_ptr_void(array_offset, argc * sizeof(i32));
    for (int i = 0; i < argc; i++) {
        size_t str_size = strlen(argv[i]) + 1;
        u32 str_offset = allocate_n_bytes(str_size);
        char* str_ptr = get_memory_ptr_for_runtime(str_offset, str_size);
        strcpy(str_ptr, argv[i]);
        array_ptr[i] = str_offset;
    }

    stub_init();

    switch_out_of_runtime();
    int ret = wasmf_main(argc, array_offset);
    switch_into_runtime();

    // Cancel any pending timeout
//    if (wasm_execution_timeout_ms) {
//        cancel_timeout();
//    }
    return ret;
}
