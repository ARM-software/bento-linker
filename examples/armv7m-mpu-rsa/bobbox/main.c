#include "bb.h"
#include <stdio.h>
#include <string.h>

#ifndef BOBBOX_KEY_SIZE
#define BOBBOX_KEY_SIZE 512
#endif

#ifndef BOBBOX_KEY_EXPONENT
#define BOBBOX_KEY_EXPONENT 65537
#endif

#ifndef BOBBOX_TEMPBUFFER_SIZE
#define BOBBOX_TEMPBUFFER_SIZE 1024
#endif

#ifndef BOBBOX_SECRET_MESSAGE
#define BOBBOX_SECRET_MESSAGE "secret message from bob! >:D"
#endif

void *bobbox_tempbuffer(size_t size) {
    static uint8_t buffer[BOBBOX_TEMPBUFFER_SIZE];
    if (size > BOBBOX_TEMPBUFFER_SIZE) {
        return NULL;
    }

    return buffer;
}

// private RSA key
static int32_t key;
static char pubkey[4*(BOBBOX_KEY_SIZE/8)]; // this overshoots a bit

int bobbox_getpubkey(char *buffer, size_t size) {
    // get our public key from the TLS box
    int err = sys_rsa_getpubkey(key, buffer, size);
    if (err) {
        return err;
    }

    // that was easy
    return 0;
}

int bobbox_recv(const void *buffer, size_t size) {
    const uint8_t *message = buffer;

    // got sent a secret message?
    printf("bobbox: recieved secret message\n");
    printf("bobbox: encrypted: '");
    for (int i = 0; i < size; i++) {
        printf("%02x", message[i]);
    }
    printf("'\n");

    printf("bobbox: decrypting...\n");
    uint8_t output[256];
    ssize_t res = sys_rsa_pkcs1_decrypt(key, message, output, sizeof(output));
    if (res < 0) {
        return res;
    }
    printf("bobbox: secret message: '%.*s'\n", 256, output);
    return 0;
}

int bobbox_init(void) {
    // generate key
    printf("bobbox: init...\n");
    printf("bobbox: generating private key...\n");
    int32_t nkey = sys_rsa_genkey(BOBBOX_KEY_SIZE, BOBBOX_KEY_EXPONENT);
    if (nkey < 0) {
        return nkey;
    }
    key = nkey;

    // print public key for fun
    printf("bobbox: serializing public key...\n");
    int err = sys_rsa_getpubkey(key, pubkey, sizeof(pubkey));
    if (err) {
        return err;
    }

    printf("bobbox: pubkey: '''\n");
    printf("%.*s\n", sizeof(pubkey), pubkey);
    printf("'''\n");

    return 0;
}

int bobbox_main(void) {
    // lets send alice a secret message!
    // first we need to get alice's public key
    printf("bobbox: getting alice's public key...\n");
    char alicepubkey[1024];
    int err = alicebox_getpubkey(alicepubkey, sizeof(alicepubkey));
    if (err) {
        return err;
    }

    int32_t alicekey = sys_rsa_frompubkey(alicepubkey, strlen(alicepubkey));
    if (alicekey < 0) {
        return alicekey;
    }

    printf("bobbox: encrypting...\n");
    uint8_t buffer[BOBBOX_KEY_SIZE/8];
    err = sys_rsa_pkcs1_encrypt(alicekey,
            BOBBOX_SECRET_MESSAGE,
            strlen(BOBBOX_SECRET_MESSAGE),
            buffer);
    if (err) {
        return err;
    }

    printf("bobbox: sending message to alice...\n");
    err = sys_send_to_alice(buffer, sizeof(buffer));
    if (err) {
        return err;
    }

    err = sys_rsa_freekey(alicekey);
    if (err) {
        return err;
    }

    return 0;
}


