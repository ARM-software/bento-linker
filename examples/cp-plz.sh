#!/bin/bash -e
#
# ignore this, I just wanted an easy way to sync files across
# multiple examples...

d2="$(pwd | cut -d'-' -f2)"

for d1 in jumptable armv7m-mpu awsm wamr wasm3
do
    dest="../$d1-$d2/$(basename $1)"
    #[ ! -f $dest ] && echo "no $dest :(" && exit 1
    [ $1 -ef $dest ] && continue
    echo "cp -u $1 $dest"
    cp -u $1 $dest
done

