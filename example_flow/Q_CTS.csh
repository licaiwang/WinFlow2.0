#!/bin/csh
# Dummy Q_CTS job for the WinFlow example flow

if ( ! -f example_flow/out/CTS.done ) then
  echo "ERROR: missing example_flow/out/CTS.done" >&2
  exit 1
endif
mkdir -p example_flow/out
sleep 1
echo "Q_CTS done at `date`" > example_flow/out/Q_CTS.done
echo "Q_CTS complete"
