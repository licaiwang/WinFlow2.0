#!/bin/csh
# Dummy FLOOR_PLAN job for the WinFlow example flow

mkdir -p example_flow/out
sleep 2
echo "FLOOR_PLAN done at `date`" > example_flow/out/FLOOR_PLAN.done
echo "FLOOR_PLAN complete"
