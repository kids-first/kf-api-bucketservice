#!/bin/bash
aws s3api list-object-versions --bucket $BUCKET_DR \
    | jq -r '.Versions[] | "\(.IsLatest),\(.VersionId),\(.Key)"' \
    > $BUCKET/glacier_inventory.txt

cat $BUCKET/glacier_inventory.txt \
    | awk '!/\/$/' \ # Dont worry about directory prefixes
    | awk '/^false,/' \ # We want all files that are not IsLatest
    | cut -f 3,2 -d ',' \
    > $BUCKET/glacier_to_delete.csv

echo There are `wc -l $BUCKET/glacier_to_delete.csv` old versions will be deleted from glacier

