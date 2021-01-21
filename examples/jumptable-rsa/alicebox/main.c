/*
 * Bento-linker example
 *
 * Copyright (c) 2020, Arm Limited. All rights reserved.
 * SPDX-License-Identifier: BSD-3-Clause
 */

#include "bb.h"
#include <stdio.h>
#include <string.h>

#ifndef ALICEBOX_KEY_SIZE
#define ALICEBOX_KEY_SIZE 1024
#endif

#ifndef ALICEBOX_KEY_EXPONENT
#define ALICEBOX_KEY_EXPONENT 65537
#endif

#ifndef ALICEBOX_SECRET_MESSAGE
#define ALICEBOX_SECRET_MESSAGE "secret message from alice! >:)"
#endif


// private RSA key
static int32_t key;
static char pubkey[8*(ALICEBOX_KEY_SIZE/8)]; // this overshoots a bit
//static char pubkey[4*(ALICEBOX_KEY_SIZE/8)]; // this overshoots a bit

int alicebox_getpubkey(char *buffer, size_t size) {
    // get our public key from the TLS box
    int err = sys_rsa_getpubkey(key, buffer, size);
    if (err) {
        return err;
    }

    // that was easy
    return 0;
}

int alicebox_recv(const void *buffer, size_t size) {
    const uint8_t *message = buffer;

    // got sent a secret message?
    printf("alicebox: recieved secret message\n");
    printf("alicebox: encrypted: '");
    for (int i = 0; i < size; i++) {
        printf("%02x", message[i]);
    }
    printf("'\n");

    printf("alicebox: decrypting...\n");
    uint8_t output[256];
    ssize_t res = sys_rsa_pkcs1_decrypt(key, message, output, sizeof(output));
    if (res < 0) {
        return res;
    }
    printf("alicebox: secret message: '%.*s'\n", 256, output);
    return 0;
}

int alicebox_init(void) {
    // generate key
    printf("alicebox: init...\n");
    printf("alicebox: generating private key...\n");
    int32_t nkey = sys_rsa_genkey(ALICEBOX_KEY_SIZE, ALICEBOX_KEY_EXPONENT);
    if (nkey < 0) {
        return nkey;
    }
    key = nkey;

    // print public key for fun
    printf("alicebox: serializing private key...\n");
    int err = sys_rsa_getprivkey(key, pubkey, sizeof(pubkey));
    if (err) {
        return err;
    }

    printf("alicebox: privkey: '''\n");
    printf("%.*s\n", sizeof(pubkey), pubkey);
    printf("'''\n");

    // print public key for fun
    printf("alicebox: serializing public key...\n");
    err = sys_rsa_getpubkey(key, pubkey, sizeof(pubkey));
    if (err) {
        return err;
    }

    printf("alicebox: pubkey: '''\n");
    printf("%.*s\n", sizeof(pubkey), pubkey);
    printf("'''\n");

    return 0;
}

int alicebox_main(void) {
    // lets send bob a secret message!
    // first we need to get bob's public key
    printf("alicebox: getting bob's public key...\n");
    char bobpubkey[1024];
    int err = bobbox_getpubkey(bobpubkey, sizeof(bobpubkey));
    if (err) {
        return err;
    }

    int32_t bobkey = sys_rsa_frompubkey(bobpubkey, strlen(bobpubkey)+1);
    if (bobkey < 0) {
        return bobkey;
    }

    printf("alicebox: encrypting...\n");
    uint8_t buffer[ALICEBOX_KEY_SIZE/8];
    err = sys_rsa_pkcs1_encrypt(bobkey,
            ALICEBOX_SECRET_MESSAGE,
            strlen(ALICEBOX_SECRET_MESSAGE)+1,
            buffer);
    if (err) {
        return err;
    }

    printf("alicebox: sending message to bob...\n");
    err = sys_send_to_bob(buffer, sizeof(buffer));
    if (err) {
        return err;
    }

    err = sys_rsa_freekey(bobkey);
    if (err) {
        return err;
    }

    return 0;
}

