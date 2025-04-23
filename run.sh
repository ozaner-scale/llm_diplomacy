#!/bin/bash

# note the summaries aren't actually used so the model doesn't matter here
uv run lm_game.py \
    --max_year 1901 \
    --num_negotiation_rounds 1 \
    --models "gpt-4o-mini, gpt-4o-mini, gpt-4o-mini, gpt-4o-mini, gpt-4o-mini, gpt-4o-mini, gpt-4o-mini"