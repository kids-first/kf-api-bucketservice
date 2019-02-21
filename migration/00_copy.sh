#!/bin/bash
aws s3 cp s3://$BUCKET s3://$BUCKET --sse --recursive
