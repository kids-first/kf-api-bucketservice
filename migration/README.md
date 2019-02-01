# Encryption and Replication Migration

These are scripts that will convert un-versioned, non-encrypted, non-replicated objects in a bucket to versioned, replicated, and encrypted objects.

## Process

The process only applies operations to one bucket.
It will need to be repeated for each bucket that needs to be migrated.

First, export `$BUCKET` and `$BUCKET_DR` to the environment.
`$BUCKET` is the source bucket in s3, and `$BUCKET_DR` is the replicated bucket.
`$BUCKET_DR` is only required if you wish to clean up old versions in the data recovery bucket, because of multiple versions having been created from multiple runs, for instance.

### Step 00

This step copies an entire bucket to itself with encryption:
```
aws s3 cp s3://$BUCKET s3://$BUCKET --recursive --sse
```
This may be done on an ec2 or local, but should be completed using EMR for large buckets.

### Step 01

This script simply accounts objects in a bucket.

### Step 02

This script validates contents for removal of the old, unencrypted, unversioned objects.
We expect that after being copied, there should be latest version of a file, and the old version of the file.
If there is not, a warning is displayed.

### Step 03

This script builds a file containing the objects for deletion in `$BUCKET/to_delete.txt`.
It may be evaluated manually before continuing.

### Step 04

This script does the actual deletion of old versions of objects from s3.
It will only delete file objects that are marked as `IsLatest=false` and `VersionId=null`.

### Step 05 (optional)

This script will look at the data replication bucket, `$BUCKET_DR`, and catelog all non-latest versions of objects

### Step 06 (optional)

This script will remove all the non-latest versions of objects from the replicated bucket.
