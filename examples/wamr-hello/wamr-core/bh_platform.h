/*
 * Copyright (C) 2019 Intel Corporation.  All rights reserved.
 * SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
 */

#ifndef DEPS_IWASM_APP_LIBS_BASE_BH_PLATFORM_H_
#define DEPS_IWASM_APP_LIBS_BASE_BH_PLATFORM_H_

#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>

typedef uint8_t uint8;
typedef int8_t int8;
typedef uint16_t uint16;
typedef int16_t int16;
typedef uint32_t uint32;
typedef int32_t int32;
typedef uint64_t uint64;
typedef int64_t int64;
typedef float float32;
typedef double float64;

#ifndef NULL
#  define NULL ((void*) 0)
#endif

#ifndef __cplusplus
#define true 1
#define false 0
#define inline __inline
#endif

// all wasm-app<->native shared source files should use WA_MALLOC/WA_FREE.
// they will be mapped to different implementations in each side
#ifndef WA_MALLOC
#define WA_MALLOC malloc
#endif

#ifndef WA_FREE
#define WA_FREE free
#endif


uint32 htonl(uint32 value);
uint32 ntohl(uint32 value);
uint16 htons(uint16 value);
uint16 ntohs(uint16 value);


// don't
__attribute__((unused)) static uint32_t errno;
static inline int bh_platform_init(void) { return 0; };
static inline void bh_platform_destroy(void) {};

#define os_printf   printf
#define os_malloc   malloc
#define os_realloc  realloc
#define os_free     free

#define BH_KB (1024)
#define BH_MB (1024*1024)
#define BH_GB (1024*1024*1024)

#define MMAP_PROT_WRITE 0
#define MMAP_PROT_READ 0
#define MMAP_PROT_EXEC 0
#define MMAP_MAP_NONE 0
#define os_mmap(ptr, size, prot, flags) \
    ((void)ptr, (void)prot, (void)flags, malloc(size))
#define os_munmap(ptr, size) \
    ((void)size, free(ptr))

#define os_dcache_flush() do {      \
        __asm__ volatile ("isb");   \
        __asm__ volatile ("dsb");   \
    } while (0)

#define os_mutex_init(m) ((void)m, 0)
#define os_mutex_lock(m) (void)m
#define os_mutex_unlock(m) (void)m
#define os_mutex_destroy(m) (void)m

#define BH_MALLOC malloc
#define BH_FREE free

// We are not worried for the WASM world since the sandbox will catch it.
//#define bh_memcpy_s(dst, dst_len, src, src_len)  memcpy(dst, src, src_len)

#endif /* DEPS_IWASM_APP_LIBS_BASE_BH_PLATFORM_H_ */
