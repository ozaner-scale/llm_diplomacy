#!/bin/bash

# Make this script executable: chmod +x run.sh

# Run the fast test mode - useful for quick debugging and validating conversation
uv run lm_game.py \
    --max_year 1905 \
    --num_negotiation_rounds 3 \
    --early_exit \
    --verbose \
    --models "gpt-4.1-nano, gpt-4.1-nano, gpt-4.1-nano, gpt-4.1-nano, gpt-4.1-nano, gpt-4.1-nano, gpt-4.1-nano"

# Uncomment below for a full game with negotiations
# python lm_game.py --max_year 1903 --num_negotiation_rounds 3