#!/bin/bash
FILE="./data/$1"
if [ -f $FILE ]; then
    echo "File already exists. $FILE"
else
    python -m scrapy runspider -o $FILE "./re_crawler/spiders/olx_re_ro.py"
fi
