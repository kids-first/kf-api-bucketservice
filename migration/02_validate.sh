#!/bin/bash
versions=`wc -l $BUCKET/inventory.txt \
    | awk '!/\/$/' \
    | tr -s ' ' \
    | cut -f 2 -d ' '`

echo There are $versions object versions in $BUCKET

let "withversion = `cat $BUCKET/inventory.txt \
    | awk '!/\/$/' \
    | cut -f 3,1 -d ',' \
    | uniq \
    | wc -l` / 2"

uniqfiles=`cat $BUCKET/inventory.txt \
    | awk '!/\/$/' \
    | cut -f 3 -d ',' \
    | uniq \
    | wc -l`

withnull=`cat $BUCKET/inventory.txt \
    | awk '!/\/$/' \
    | awk '/^(true|false),null/' \
    | cut -f 3 -d ',' \
    | uniq \
    | wc -l`

echo There are $uniqfiles unique files
echo There are $withversion files with at least 2 versions
echo There are $withnull files with a null version id

if [[ $uniqfiles -ne $withversion || $uniqfiles -ne $withnull ]]; then
    echo "!! WARNING!!!!!!!!!!!
!! The above numbers are not in agreement.
!! This could mean that some files were not copied or old versions were already deleted.
!! Please make sure you want to continue"
fi
echo "Continuing will remove ONLY file objects that are marked as NOT the latest version and have a version id of 'null'"
