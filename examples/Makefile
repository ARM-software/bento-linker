override TARGETS += decoder
override TARGETS += decoder_unsafe
override TARGETS += decoder_stream
override TARGETS += decoder_seek
override TARGETS += decoder_rust
override TARGETS += decoder_rust_stream
override TARGETS += decoder_rust_seek

DEBUG ?= 0
SPEED ?= 0

all build: $(TARGETS)

size: $(TARGETS)
	$(strip nm -So -td $^ \
		| grep '\<glz_decode\>' \
		| awk -F '[: ]' '{printf "%-24s %d bytes\n",$$1":",$$3}')

clean:
	rm -f $(TARGETS)

%: %.c
ifneq ($(DEBUG),0)
	gcc -g -std=c99 -pedantic -Wno-format $< -o $@
else
ifneq ($(SPEED),0)
	gcc -O3 -std=c99 -pedantic -Wno-format $< -o $@
else
	gcc -Os -std=c99 -pedantic -Wno-format $< -o $@
endif
endif

%: %.rs
ifneq ($(DEBUG),0)
	rustc -g $< -o $@
else
ifneq ($(SPEED),0)
	rustc -C opt-level=3 $< -o $@
else
	rustc -C opt-level=s $< -o $@
endif
endif
