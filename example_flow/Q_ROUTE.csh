#!/bin/csh
# Dummy Q_ROUTE job for the WinFlow example flow

if ( ! -f example_flow/out/ROUTE.done ) then
  echo "ERROR: missing example_flow/out/ROUTE.done" >&2
  exit 1
endif
mkdir -p example_flow/out
sleep 1
echo "Q_ROUTE done at `date`" > example_flow/out/Q_ROUTE.done
echo "Q_ROUTE complete"
