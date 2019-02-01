#!/bin/bash
cat $BUCKET/to_delete.csv \
  | awk -F ',' '{print "{Key="$2",VersionId="$1"}"}' \
  | gxargs -n100 \
  | sed 's/ /,/g' \
  | gxargs -L1 -I {} aws s3api delete-objects --bucket $BUCKET --delete Objects=\[{}\],Quiet=false
