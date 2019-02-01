#!/bin/bash
mkdir $BUCKET
aws s3api list-object-versions --bucket $BUCKET | jq -r '.Versions[] | "\(.IsLatest),\(.VersionId),\(.Key)"' > $BUCKET/inventory.txt
echo Saved current bucket state to $BUCKET/inventory
