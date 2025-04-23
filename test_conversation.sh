#!/bin/bash

# Make this script executable: chmod +x test_conversation.sh

# Run a focused test of only the conversation functionality
# with fast failure and detailed output to quickly diagnose issues
python lm_game.py \
    --max_year 1905 \
    --num_negotiation_rounds 3 \
    --early_exit \
    --verbose \
    --models "gpt-4.1-nano, gpt-4.1-nano, gpt-4.1-nano, gpt-4.1-nano, gpt-4.1-nano, gpt-4.1-nano, gpt-4.1-nano"

# Uncomment if you want to test with a specific model
# python lm_game.py --max_year 1901 --num_negotiation_rounds 1 --early_exit --verbose --models "claude-3-5-sonnet-20241022, claude-3-5-sonnet-20241022, claude-3-5-sonnet-20241022, claude-3-5-sonnet-20241022, claude-3-5-sonnet-20241022, claude-3-5-sonnet-20241022, claude-3-5-sonnet-20241022" 