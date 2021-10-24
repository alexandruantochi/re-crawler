#!/bin/bash
python -m scrapy runspider -o "./data/$1" "./re_crawler/spiders/olx_re_ro.py"