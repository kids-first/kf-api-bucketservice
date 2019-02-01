#!/bin/bash
cat $BUCKET/inventory.txt \
    | awk '/^false,' \ # Mark only files that are not the latest version
    | awk '!/\/$/' \ # Dont mark files that are directory prefixes
    | cut -f 3,2 -d ',' \
    | awk '/,null$/' \ # Mark files that have no version ID
    > $BUCKET/to_delete.csv

echo There are `wc -l $BUCKET/to_delete.csv` files to be deleted
