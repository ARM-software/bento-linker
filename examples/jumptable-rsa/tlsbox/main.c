#include "bb.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "mbedtls/entropy.h"
#include "mbedtls/ctr_drbg.h"
#include "mbedtls/bignum.h"
#include "mbedtls/rsa.h"

#ifndef TLSBOX_TEMPBUFFER_SIZE
#define TLSBOX_TEMPBUFFER_SIZE (4*1024)
#endif

#ifndef TLSBOX_KEY_COUNT
#define TLSBOX_KEY_COUNT 4
#endif

// binding to system source of entropy
static int tlsbox_entropy_poll(void *eh, uint8_t *output,
        size_t len, size_t *olen) {
    ssize_t res = sys_entropy_poll(output, len);
    if (res < 0) {
        return res;
    }

    *olen = res;
    return 0;
}

// seed random-bit-generator
static bool tlsbox_drbg_initialized = false;
static mbedtls_ctr_drbg_context tlsbox_drbg;

int tlsbox_drbg_seed(void) {
    tlsbox_drbg_initialized = false;

    // create entropy sources
    printf("tlsbox: creating entropy sources...\n");
    mbedtls_entropy_context entropy;
    mbedtls_entropy_init(&entropy);
    mbedtls_entropy_add_source(&entropy,
        tlsbox_entropy_poll, NULL,
        1, // TODO this correct? hint it's not
        MBEDTLS_ENTROPY_SOURCE_STRONG);

    // seeding random number generator
    printf("tlsbox: seeding random number generator...\n");
    mbedtls_ctr_drbg_init(&tlsbox_drbg);
    int err = mbedtls_ctr_drbg_seed(&tlsbox_drbg,
            mbedtls_entropy_func, &entropy,
            NULL, 0);
    if (err) {
        return err;
    }

    tlsbox_drbg_initialized = true;
    return 0;
}


// storage of keys contained in this box
static mbedtls_rsa_context rsa_contexts[TLSBOX_KEY_COUNT];

static int32_t tlsbox_rsa_findnextkey(void) {
    for (int i = 0; i < TLSBOX_KEY_COUNT; i++) {
        int res = mbedtls_rsa_check_pubkey(&rsa_contexts[i]);
        if (res < 0 && res != MBEDTLS_ERR_RSA_KEY_CHECK_FAILED) {
            // actual error
            return res;
        }

        if (res == MBEDTLS_ERR_RSA_KEY_CHECK_FAILED) {
            // found unused rsa_key
            return i+1;
        }
    }

    // no more slots left
    return -ENOMEM;
}

static int tlsbox_rsa_fromkey(int32_t key, mbedtls_rsa_context **context) {
    key = key - 1;
    if (!(key >= 0 && key < TLSBOX_KEY_COUNT)) {
        return -EINVAL;
    }
    mbedtls_rsa_context *rsa = &rsa_contexts[key];

    // must at minimum be pubkey
    int res = mbedtls_rsa_check_pubkey(rsa);
    if (res) {
        return res;
    }

    *context = rsa;
    return 0;
}

int32_t tlsbox_rsa_genkey(size_t key_size, int32_t exponent) {
    // needs drbg to be seeded
    if (!tlsbox_drbg_initialized) {
        return -EINVAL;
    }

    // allocate RSA key
    printf("tlsbox: allocating RSA key...\n");
    int32_t key = tlsbox_rsa_findnextkey();
    if (key < 0) {
        return key;
    }
    mbedtls_rsa_context *rsa = &rsa_contexts[key-1];

    // generate RSA key
    printf("tlsbox: generating RSA key...\n");
    mbedtls_rsa_init(rsa, MBEDTLS_RSA_PKCS_V15, 0);
    int err = mbedtls_rsa_gen_key(rsa,
            mbedtls_ctr_drbg_random, &tlsbox_drbg,
            key_size, exponent);
    if (err) {
        return err;
    }

    // success?
    return key;
}

int tlsbox_rsa_freekey(int32_t key) {
    mbedtls_rsa_context *rsa;
    int err = tlsbox_rsa_fromkey(key, &rsa);
    if (err) {
        return err;
    }
    
    mbedtls_rsa_free(rsa);
    return 0;
}

int tlsbox_rsa_getprivkey(int32_t key, char *privkey, size_t size) {
    mbedtls_rsa_context *rsa;
    int err = tlsbox_rsa_fromkey(key, &rsa);
    if (err) {
        return err;
    }

    printf("tlsbox: serializing RSA private key...\n");
    mbedtls_mpi N, P, Q, D, E;
    mbedtls_mpi_init(&N);
    mbedtls_mpi_init(&P);
    mbedtls_mpi_init(&Q);
    mbedtls_mpi_init(&D);
    mbedtls_mpi_init(&E);
    err = mbedtls_rsa_export(rsa, &N, &P, &Q, &D, &E);
    if (err) {
        return err;
    }

    mbedtls_mpi *mpis[5] = {&N, &P, &Q, &D, &E};
    for (int i = 0; i < 5; i++) {
        size_t diff;
        err = mbedtls_mpi_write_string(mpis[i], 16,
                privkey, size, &diff);
        if (err) {
            return err;
        }

        // replace NULL with newline if we're not the last entry
        if (i != 5-1) {
            privkey[diff-1] = '\n';
        }

        privkey += diff;
        size -= diff;
    }

    mbedtls_mpi_free(&N);
    mbedtls_mpi_free(&P);
    mbedtls_mpi_free(&Q);
    mbedtls_mpi_free(&D);
    mbedtls_mpi_free(&E);
    return 0;
}

int tlsbox_rsa_getpubkey(int32_t key, char *pubkey, size_t size) {
    mbedtls_rsa_context *rsa;
    int err = tlsbox_rsa_fromkey(key, &rsa);
    if (err) {
        return err;
    }

    printf("tlsbox: serializing RSA public key...\n");
    mbedtls_mpi N, E;
    mbedtls_mpi_init(&N);
    mbedtls_mpi_init(&E);
    err = mbedtls_rsa_export(rsa, &N, NULL, NULL, NULL, &E);
    if (err) {
        return err;
    }

    mbedtls_mpi *mpis[2] = {&N, &E};
    for (int i = 0; i < 2; i++) {
        size_t diff;
        err = mbedtls_mpi_write_string(mpis[i], 16,
                pubkey, size, &diff);
        if (err) {
            return err;
        }

        // replace NULL with newline if we're not the last entry
        if (i != 2-1) {
            pubkey[diff-1] = '\n';
        }

        pubkey += diff;
        size -= diff;
    }

    mbedtls_mpi_free(&N);
    mbedtls_mpi_free(&E);
    return 0;
}

int32_t tlsbox_rsa_fromprivkey(const char *privkey, size_t size) {
    // allocate RSA key
    printf("tlsbox: allocating RSA key...\n");
    int32_t key = tlsbox_rsa_findnextkey();
    if (key < 0) {
        return key;
    }
    mbedtls_rsa_context *rsa = &rsa_contexts[key-1];

    printf("tlsbox: deserializing RSA private key...\n");
    mbedtls_mpi N, P, Q, D, E;
    mbedtls_mpi_init(&N);
    mbedtls_mpi_init(&P);
    mbedtls_mpi_init(&Q);
    mbedtls_mpi_init(&D);
    mbedtls_mpi_init(&E);

    mbedtls_mpi *mpis[5] = {&N, &P, &Q, &D, &E};

    // kinda annoying we need this
    char *temp = malloc(strlen(privkey));
    if (!temp) {
        return -ENOMEM;
    }

    for (int i = 0; i < 5; i++) {
        size_t diff = strcspn(privkey, "\n");
        if (diff == 0 || (privkey[diff] == '\0' && i != 5-1)) {
            return -EINVAL;
        }

        memcpy(temp, privkey, diff);
        temp[diff] = '\0';
        int err = mbedtls_mpi_read_string(mpis[i], 16, temp);
        if (err) {
            return err;
        }

        privkey += diff + 1;
    }

    free(temp);

    // build the actual RSA key
    int err = mbedtls_rsa_import(rsa, &N, &P, &Q, &D, &E);
    if (err) {
        return err;
    }

    err = mbedtls_rsa_complete(rsa);
    if (err) {
        return err;
    }

    mbedtls_mpi_free(&N);
    mbedtls_mpi_free(&P);
    mbedtls_mpi_free(&Q);
    mbedtls_mpi_free(&D);
    mbedtls_mpi_free(&E);

    return key;
}

int32_t tlsbox_rsa_frompubkey(const char *pubkey, size_t size) {
    // allocate RSA key
    printf("tlsbox: allocating RSA key...\n");
    int32_t key = tlsbox_rsa_findnextkey();
    if (key < 0) {
        return key;
    }
    mbedtls_rsa_context *rsa = &rsa_contexts[key-1];

    printf("tlsbox: deserializing RSA public key...\n");
    mbedtls_mpi N, E;
    mbedtls_mpi_init(&N);
    mbedtls_mpi_init(&E);

    mbedtls_mpi *mpis[2] = {&N, &E};

    // kinda annoying we need this
    char *temp = malloc(strlen(pubkey));
    if (!temp) {
        return -ENOMEM;
    }

    for (int i = 0; i < 2; i++) {
        size_t diff = strcspn(pubkey, "\n");
        if (diff == 0 || (pubkey[diff] == '\0' && i != 2-1)) {
            return -EINVAL;
        }

        memcpy(temp, pubkey, diff);
        temp[diff] = '\0';
        int err = mbedtls_mpi_read_string(mpis[i], 16, temp);
        if (err) {
            return err;
        }

        pubkey += diff + 1;
    }

    free(temp);

    // build the actual RSA key
    int err = mbedtls_rsa_import(rsa, &N, NULL, NULL, NULL, &E);
    if (err) {
        return err;
    }

    err = mbedtls_rsa_complete(rsa);
    if (err) {
        return err;
    }

    mbedtls_mpi_free(&N);
    mbedtls_mpi_free(&E);

    return key;
}

int tlsbox_rsa_pkcs1_encrypt(int32_t key,
        const void *input, size_t input_size, void *output) {
    // needs drbg to be seeded
    if (!tlsbox_drbg_initialized) {
        return -EINVAL;
    }

    mbedtls_rsa_context *rsa;
    int err = tlsbox_rsa_fromkey(key, &rsa);
    if (err) {
        return err;
    }

    err = mbedtls_rsa_pkcs1_encrypt(rsa,
            mbedtls_ctr_drbg_random, &tlsbox_drbg,
            MBEDTLS_RSA_PUBLIC,
            input_size, input, output);
    if (err) {
        return err;
    }

    return 0;
}

ssize_t tlsbox_rsa_pkcs1_decrypt(int32_t key,
        const void *input, void *output, size_t output_size) {
    // needs drbg to be seeded
    if (!tlsbox_drbg_initialized) {
        return -EINVAL;
    }

    mbedtls_rsa_context *rsa;
    int err = tlsbox_rsa_fromkey(key, &rsa);
    if (err) {
        return err;
    }

    err = mbedtls_rsa_pkcs1_decrypt(rsa,
            mbedtls_ctr_drbg_random, &tlsbox_drbg,
            MBEDTLS_RSA_PRIVATE,
            &output_size, input, output, output_size);
    if (err) {
        return err;
    }

    return output_size;
}

