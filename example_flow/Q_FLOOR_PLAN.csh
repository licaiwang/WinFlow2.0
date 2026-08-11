#!/bin/csh
# Dummy Q_FLOOR_PLAN job for the WinFlow example flow

if ( ! -f example_flow/out/FLOOR_PLAN.done ) then
  echo "ERROR: missing example_flow/out/FLOOR_PLAN.done" >&2
  exit 1
endif
mkdir -p example_flow/out
sleep 1
echo "Q_FLOOR_PLAN done at `date`" > example_flow/out/Q_FLOOR_PLAN.done
echo "Q_FLOOR_PLAN complete"
