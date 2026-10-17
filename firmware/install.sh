#!/bin/sh
# Same entry as the on-device demo.
exec "$(CDPATH= cd -- "$(dirname "$0")" && pwd)/demo.sh"
