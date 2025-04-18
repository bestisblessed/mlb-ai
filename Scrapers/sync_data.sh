#!/bin/bash

# Pull data from my server

rsync -avz --progress Trinity:~/mlb-ai/Scrapers/data/ data/

