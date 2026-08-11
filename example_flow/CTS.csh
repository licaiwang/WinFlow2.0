#!/bin/csh
# Dummy CTS job for the WinFlow example flow

if ( ! -f example_flow/out/PLACE.done ) then
  echo "ERROR: missing example_flow/out/PLACE.done" >&2
  exit 1
endif
mkdir -p example_flow/out
sleep 2
echo "CTS done at `date`" > example_flow/out/CTS.done
echo "CTS complete"
