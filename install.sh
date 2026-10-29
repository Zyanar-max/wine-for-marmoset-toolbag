#!/bin/sh
# Wine for Marmoset Toolbag - run with sh install.sh   (undo: sh install.sh --uninstall)
cd "$(dirname "$0")" && exec python3 installer.py "$@"
