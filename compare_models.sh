#!/bin/bash

# Make this script executable: chmod +x compare_models.sh

# This script tests conversations with different models to find the best one
# It stops after the first successful model to save time

MODELS=("gpt-4" "gpt-4o" "gpt-3.5-turbo" "claude-3-opus-20240229" "claude-3-sonnet-20240229")

echo "Starting model comparison for conversation format..."
echo "Testing models in this order: ${MODELS[@]}"
echo 

for MODEL in "${MODELS[@]}"
do
    echo "-----------------------------------------------------"
    echo "Testing conversation format with model: $MODEL"
    echo "-----------------------------------------------------"
    
    # Try to run with the current model, capturing output and exit code
    python lm_game.py \
        --max_year 1901 \
        --num_negotiation_rounds 1 \
        --early_exit \
        --verbose \
        --models "$MODEL, $MODEL, $MODEL, $MODEL, $MODEL, $MODEL, $MODEL" > model_test_output.log 2>&1
    
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -eq 0 ]; then
        echo "SUCCESS! Model $MODEL works with the conversation format."
        echo "This is your best model choice for conversations."
        echo "Full output is in model_test_output.log"
        exit 0
    else
        echo "FAILED: Model $MODEL had issues with the conversation format."
        echo "Error details from log:"
        grep -A 5 "CONVERSATION ERROR" model_test_output.log | head -6
        echo "..."
        echo
    fi
done

echo "All models failed. Check model_test_output.log for details."
exit 1 