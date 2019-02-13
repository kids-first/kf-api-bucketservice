#!/bin/bash
cat $BUCKET/to_delete.csv \
  | awk -F ',' '{print "{Key="$3",VersionId="$2"}"}' \
  | xargs -L100 \
  | sed 's/} {/},{/g' \
  | xargs -L1 -I {} aws s3api delete-objects --bucket $BUCKET --delete Objects=\[{}\],Quiet=false
