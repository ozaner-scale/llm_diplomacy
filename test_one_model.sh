#!/bin/bash

# Make this script executable: chmod +x test_one_model.sh

# Usage: ./test_one_model.sh [model_name]
# Example: ./test_one_model.sh gpt-4o

MODEL=${1:-"gpt-4o"}

echo "Testing conversation format with model: $MODEL"

# Run a focused test with a single model on all powers
python lm_game.py \
    --max_year 1901 \
    --num_negotiation_rounds 1 \
    --early_exit \
    --verbose \
    --models "$MODEL, $MODEL, $MODEL, $MODEL, $MODEL, $MODEL, $MODEL"

echo "Test complete for $MODEL" 