/*
 * Bento-linker example
 *
 * Copyright (c) 2020, Arm Limited. All rights reserved.
 * SPDX-License-Identifier: BSD-3-Clause
 */

#include "bb.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "lfs.h"

int lfsbox_bd_read(const struct lfs_config *c, lfs_block_t block,
        lfs_off_t off, void *buffer, lfs_size_t size) {
    return bd_read(block, off, buffer, size);
}

int lfsbox_bd_prog(const struct lfs_config *c, lfs_block_t block,
        lfs_off_t off, const void *buffer, lfs_size_t size) {
    return bd_prog(block, off, buffer, size);
}

int lfsbox_bd_erase(const struct lfs_config *c, lfs_block_t block) {
    return bd_erase(block);
}

int lfsbox_bd_sync(const struct lfs_config *c) {
    return bd_sync();
}

static void lfsbox_configure(struct lfs_config *cfg) {
    memset(cfg, 0, sizeof(struct lfs_config));
    cfg->read = lfsbox_bd_read;
    cfg->prog = lfsbox_bd_prog;
    cfg->erase = lfsbox_bd_erase;
    cfg->sync = lfsbox_bd_sync;
    cfg->read_size = 1;
    cfg->prog_size = 1;
    cfg->block_size = bd_block_size();
    cfg->block_count = bd_block_count();
    cfg->block_cycles = 100;
    cfg->cache_size = 16;
    cfg->lookahead_size = 16;
}

lfs_t lfs;
struct lfs_config cfg;

#define FILE_COUNT 4
static bool files_opened[FILE_COUNT];
static lfs_file_t files[FILE_COUNT];

int lfsbox_format(void) {
    lfsbox_configure(&cfg);
    return lfs_format(&lfs, &cfg);
}

int lfsbox_mount(void) {
    lfsbox_configure(&cfg);
    int err = lfs_mount(&lfs, &cfg);
    if (err) {
        return err;
    }

    memset(files_opened, 0, FILE_COUNT);
    return 0;
}

int lfsbox_unmount(void) {
    return lfs_unmount(&lfs);
}

int lfsbox_rename(const char *oldpath, const char *newpath) {
    return lfs_rename(&lfs, oldpath, newpath);
}

int32_t lfsbox_file_open(const char *path, uint32_t flags) {
    int fd;
    for (fd = 0; fd < FILE_COUNT; fd++) {
        if (!files_opened[fd]) {
            break;
        }
    }

    if (fd >= FILE_COUNT) {
        return -EMFILE;
    }

    int err = lfs_file_open(&lfs, &files[fd], path, flags);
    if (err) {
        return err;
    }

    files_opened[fd] = true;
    return fd;
}

int lfsbox_file_close(int32_t fd) {
    if (fd >= FILE_COUNT) {
        return -ENFILE;
    }

    int err = lfs_file_close(&lfs, &files[fd]);
    if (err) {
        return err;
    }

    files_opened[fd] = false;
    return 0;
}

ssize_t lfsbox_file_read(int32_t fd, void *buffer, size_t size) {
    if (fd >= FILE_COUNT) {
        return -ENFILE;
    }

    return lfs_file_read(&lfs, &files[fd], buffer, size);
}

ssize_t lfsbox_file_write(int32_t fd, const void *buffer, size_t size) {
    if (fd >= FILE_COUNT) {
        return -ENFILE;
    }

    return lfs_file_write(&lfs, &files[fd], buffer, size);
}

int32_t lfsbox_file_seek(int32_t fd, int32_t off, uint32_t whence) {
    if (fd >= FILE_COUNT) {
        return -ENFILE;
    }

    return lfs_file_seek(&lfs, &files[fd], off, whence);
}
