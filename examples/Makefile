override TARGETS += decoder
override TARGETS += decoder_unsafe
override TARGETS += decoder_stream
override TARGETS += decoder_seek
override TARGETS += decoder_rust

all build: $(TARGETS)

size: $(TARGETS)
	$(strip nm -So -td $^ \
		| grep '\<glz_decode\>' \
		| awk -F '[: ]' '{printf "%-16s %d bytes\n",$$1":",$$3}')

clean:
	rm -f $(TARGETS)

%: %.c
ifdef DEBUG
	gcc -g -std=c99 -pedantic -Wno-format $< -o $@
else
	gcc -Os -std=c99 -pedantic -Wno-format $< -o $@
endif

%: %.rs
	rustc -C opt-level=s $< -o $@
