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

# Some buckets may have files with versions already assigned, but have not been replicated
# We will ignore the check for all files having an old null version
# if [[ $uniqfiles -ne $withversion || $uniqfiles -ne $withnull ]]; then
#     echo "!! WARNING!!!!!!!!!!!
# !! The above numbers are not in agreement.
# !! This could mean that some files were not copied or old versions were already deleted.
# !! Please make sure you want to continue"
# fi
# echo "Continuing will remove ONLY file objects that are marked as NOT the latest version and have a version id of 'null'"

notbackedup=`comm -23 <(sort $BUCKET/inventory.txt | awk '/^true,/') <(sort $BUCKET_DR/inventory.txt | awk '/^true,/')`
numnotbackedup=`echo "$notbackedup" | wc -l`
if [[ $numnotbackedup -gt 0 ]]; then
    echo "!! WARNING!!!!!!!!!!!"
    echo There are $numnotbackedup files that are marked as latest and have not been replicated!!!
    echo Consider investigating before continuing!
fi

todelete=`comm -23 <(sort $BUCKET/inventory.txt | awk '/^false,/') <(sort $BUCKET_DR/inventory.txt)`
echo There are `echo "$todelete" | wc -l` files that are not-latest versions and have no replicated object that may be deleted
