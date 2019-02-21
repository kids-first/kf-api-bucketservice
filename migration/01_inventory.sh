#!/bin/bash
mkdir $BUCKET
mkdir $BUCKET_DR

aws s3api list-object-versions --bucket $BUCKET | jq -r '.Versions[] | "\(.IsLatest),\(.VersionId),\(.Key)"' > $BUCKET/inventory.txt
echo Saved current bucket state to $BUCKET/inventory.txt

aws s3api list-object-versions --bucket $BUCKET_DR | jq -r '.Versions[] | "\(.IsLatest),\(.VersionId),\(.Key)"' > $BUCKET_DR/inventory.txt
echo Saved current replication bucket state to $BUCKET_DR/inventory.txt
