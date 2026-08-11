#!/bin/csh
# Dummy Q_PLACE job for the WinFlow example flow

if ( ! -f example_flow/out/PLACE.done ) then
  echo "ERROR: missing example_flow/out/PLACE.done" >&2
  exit 1
endif
mkdir -p example_flow/out
sleep 1
echo "Q_PLACE done at `date`" > example_flow/out/Q_PLACE.done
echo "Q_PLACE complete"
