###### BENTO-BOX AUTOGENERATED ######

TARGET           ?= sys.elf

DEBUG            ?= 0
LTO              ?= 1
ASSERTS          ?= 1
CC               = arm-none-eabi-gcc
OBJCOPY          = arm-none-eabi-objcopy
OBJDUMP          = arm-none-eabi-objdump
AR               = arm-none-eabi-ar
SIZE             = arm-none-eabi-size
GDB              = arm-none-eabi-gdb
GDBADDR          ?= localhost
GDBPORT          ?= 3333
TTY              ?= $(firstword $(wildcard /dev/ttyACM* /dev/ttyUSB*))
BAUD             ?= 115200

SRC += .
SRC += nrfx/drivers/src
SRC += wasm3/source
INC += .
INC += nrfx
INC += cmsis
INC += nrfx/drivers/include
INC += nrfx/mdk
INC += nrfx/templates
INC += wasm3/source
LIB += m
LIB += c
LIB += gcc
LIB += nosys

OBJ := $(patsubst %.c,%.o,$(wildcard $(patsubst %,%/*.c,$(SRC))))
OBJ += $(patsubst %.s,%.o,$(wildcard $(patsubst %,%/*.s,$(SRC))))
OBJ += $(patsubst %.S,%.o,$(wildcard $(patsubst %,%/*.S,$(SRC))))
DEP := $(patsubst %.o,%.d,$(OBJ))
LDSCRIPT := $(firstword $(wildcard $(patsubst %,%/*.ld,$(SRC))))
BOXES += lfsbox/lfsbox.box

override CFLAGS += -g
ifneq ($(DEBUG),0)
override CFLAGS += -O0
else
ifeq ($(ASSERTS),0)
override CFLAGS += -DNDEBUG
endif
override CFLAGS += -Os
ifneq ($(LTO),0)
override CFLAGS += -flto
endif
endif
override CFLAGS += -mthumb
override CFLAGS += -mcpu=cortex-m4
override CFLAGS += -mfpu=fpv4-sp-d16
override CFLAGS += -mfloat-abi=softfp
override CFLAGS += -std=c99
override CFLAGS += -Wall -Wno-format
override CFLAGS += -fno-common
override CFLAGS += -ffunction-sections
override CFLAGS += -fdata-sections
override CFLAGS += -ffreestanding
override CFLAGS += -fno-builtin
override CFLAGS += -fshort-enums
override CFLAGS += $(patsubst %,-I%,$(INC))

override ASMFLAGS += $(CFLAGS)

override LDFLAGS += $(CFLAGS)
override LDFLAGS += $(addprefix -T,$(LDSCRIPT))
override LDFLAGS += $(patsubst %,-L%,$(SRC))
override LDFLAGS += -Wl,--start-group $(patsubst %,-l%,$(LIB)) -Wl,--end-group
override LDFLAGS += -static
override LDFLAGS += --specs=nano.specs
override LDFLAGS += --specs=nosys.specs
override LDFLAGS += -Wl,--gc-sections
override LDFLAGS += -Wl,-static
override LDFLAGS += -Wl,-z,muldefs

### __box_abort glue ###
override LDFLAGS += -Wl,--wrap,abort
override LDFLAGS += -Wl,--wrap,exit

### __box_write glue ###
override LDFLAGS += -Wl,--wrap,printf
override LDFLAGS += -Wl,--wrap,vprintf
override LDFLAGS += -Wl,--wrap,fprintf
override LDFLAGS += -Wl,--wrap,vfprintf
override LDFLAGS += -Wl,--wrap,fflush

### user provided flags ###

override CFLAGS += -DNRF52840_XXAA='1'
override CFLAGS += -DNRFX_CLOCK_ENABLED='1'
override CFLAGS += -DNRFX_TIMER0_ENABLED='1'
override CFLAGS += -DNRFX_TIMER_ENABLED='1'
override CFLAGS += -DNRFX_UARTE0_ENABLED='1'
override CFLAGS += -DNRFX_UARTE_ENABLED='1'
override CFLAGS += -DPRIi64='"lli"'
override CFLAGS += -DPRIu64='"llu"'

override CFLAGS += -Wno-unused-function
override CFLAGS += -Wno-unused-variable
override CFLAGS += -Wno-strict-aliasing

# target rule
$(TARGET): $(OBJ) $(BOXES) $(LDSCRIPT)
	$(CC) $(OBJ) $(BOXES) $(LDFLAGS) -o $@

# a .box is a .elf containing a single section for each loadable memory region
%.box: %.elf %.box.flash %.box.box.lfsbox.flash
	$(strip $(OBJCOPY) $< $@ \
	    -I binary \
	    -O elf32-littlearm \
	    -B arm \
	    --strip-all \
	    --remove-section=* \
	    --add-section .box.sys.flash=$(word 2,$^) \
	    --change-section-address .box.sys.flash=0x00000000 \
	    --set-section-flags .box.sys.flash=contents,alloc,load,readonly,data \
	    --add-section .box.sys.box.lfsbox.flash=$(word 3,$^) \
	    --change-section-address .box.sys.box.lfsbox.flash=0x000f0000 \
	    --set-section-flags .box.sys.box.lfsbox.flash=contents,alloc,load,readonly,data)

%.box.flash: %.elf
	$(strip $(OBJCOPY) $< $@ \
	    --only-section .text \
	    --only-section .data \
	    --only-section .isr_vector \
	    -O binary)

%.box.box.lfsbox.flash: %.elf
	$(strip $(OBJCOPY) $< $@ \
	    --only-section .box.lfsbox.flash \
	    -O binary)

### rules ###

# default rule
.PHONY: all build
all build: $(TARGET)

# computing size size is a bit complicated as each .elf includes its boxes, we
# want independent sizes.
.PHONY: size
size: $(TARGET) $(BOXES)
	$(strip ( $(SIZE) $^ ; \
	    $(MAKE) -s --no-print-directory -C lfsbox size ) | awk '\
	        function f(t, d, b, n) { \
	            printf "%7d %7d %7d %7d %7x %s\n", \
	            t, d, b, t+d+b, t+d+b, n} \
	        NR==1 {print} \
	        NR==2 {t=$$1; d=$$2; b=$$3; n=$$6} \
	        NR>=3 && NR<4 {bt+=$$1} \
	        NR>=4 && /^([ \t]+[0-9]+){3,}/ && !/TOTALS/ { \
	            l[NR-4]=$$0; bd+=$$2; bb+=$$3} \
	        END {f(t-bt, d, b, n)} \
	        END {for (i in l) print l[i]} \
	        END {f(t, d, b+bd+bb, "(TOTALS)")}')

.PHONY: debug
debug: $(TARGET)
	echo '$$qRcmd,68616c74#fc' | nc -N $(GDBADDR) $(GDBPORT) && echo # halt
	$(strip $(GDB) $< \
	    -ex "target remote $(GDBADDR):$(GDBPORT)")
	echo '$$qRcmd,676f#2c' | nc -N $(GDBADDR) $(GDBPORT) && echo # go

.PHONY: flash
flash: $(TARGET)
	echo '$$qRcmd,68616c74#fc' | nc -N $(GDBADDR) $(GDBPORT) && echo # halt
	$(strip $(GDB) $< \
	    -ex "target remote $(GDBADDR):$(GDBPORT)" \
	    -ex "load" \
	    -ex "monitor reset" \
	    -batch)

.PHONY: reset
reset:
	echo '$$qRcmd,7265736574#37' | nc -N $(GDBADDR) $(GDBPORT) && echo # reset
	echo '$$qRcmd,676f#2c' | nc -N $(GDBADDR) $(GDBPORT) && echo # go

.PHONY: cat
cat:
	stty -F $(TTY) sane nl $(BAUD)
	cat $(TTY)

.PHONY: tags
tags:
	$(strip ctags --totals \
	    $(shell find -H $(INC) -name '*.h') \
	    $(wildcard $(patsubst %,%/*.c,$(SRC))) \
	    $(wildcard $(patsubst %,%/*.s,$(SRC))) \
	    $(wildcard $(patsubst %,%/*.S,$(SRC))))

.PHONY: $(shell make -s -C lfsbox lfsbox.box -q || echo lfsbox/lfsbox.box)
lfsbox/lfsbox.box:
	@echo "================ make -C lfsbox ================"
	$(MAKE) --no-print-directory -C lfsbox lfsbox.box
	@echo "================================================"

# header dependencies
-include $(DEP)

%.bin: %.elf
	$(OBJCOPY) -O binary $< $@

%.o: %.c
	$(CC) -c -MMD -MP $(CFLAGS) $< -o $@

%.s: %.c
	$(CC) -S -MMD -MP $(CFLAGS) $< -o $@

%.o: %.s
	$(CC) -c -MMD -MP $(ASMFLAGS) $< -o $@

%.o: %.S
	$(CC) -c -MMD -MP $(ASMFLAGS) $< -o $@

.PHONY: clean
clean:
	rm -f $(TARGET) $(BOXES)
	rm -f $(OBJ)
	rm -f $(DEP)
	$(MAKE) -C lfsbox clean

