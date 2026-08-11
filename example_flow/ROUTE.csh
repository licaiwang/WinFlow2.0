#!/bin/csh
# Dummy ROUTE job for the WinFlow example flow

if ( ! -f example_flow/out/CTS.done ) then
  echo "ERROR: missing example_flow/out/CTS.done" >&2
  exit 1
endif
mkdir -p example_flow/out
sleep 2
echo "ROUTE done at `date`" > example_flow/out/ROUTE.done
echo "ROUTE complete"
