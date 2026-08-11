#!/bin/csh
# Dummy PLACE job for the WinFlow example flow

if ( ! -f example_flow/out/FLOOR_PLAN.done ) then
  echo "ERROR: missing example_flow/out/FLOOR_PLAN.done" >&2
  exit 1
endif
mkdir -p example_flow/out
sleep 2
echo "PLACE done at `date`" > example_flow/out/PLACE.done
echo "PLACE complete"
