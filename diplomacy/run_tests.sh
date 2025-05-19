#!/bin/bash
# Syntax: ./run_tests               -- Run tests in parallel across CPUs
#         ./run_tests <nb_cores>    -- Run tests in parallel across this number of CPUs
#         ./run_tests 0             -- Only runs the pylint tests
export PYTHONIOENCODING=utf-8
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
FAILED=0

# Running pytest
if [ "${1:-auto}" != "0" ]; then
    pytest -v --forked -n "${1:-auto}" diplomacy || FAILED=1
fi

# Exiting
if [[ "$FAILED" -eq 1 ]]; then
    echo "*** TESTS FAILED ***"
    exit 1
else
    echo "All tests passed."
    exit 0
fi
