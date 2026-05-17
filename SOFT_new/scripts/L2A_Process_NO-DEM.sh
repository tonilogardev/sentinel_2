#!/bin/bash
# Sen2Cor 2.12.03 via Wine 11 — detect variant from script name
# Usage: L2A_Process_{VARIANT}.sh [--output_dir DIR] SAFE_DIR [extra args...]

SEN2COR_DIR="/opt/sen2cor-2.12.03"

# Detect variant: L2A_Process_NO-DEM.sh → NO-DEM, etc.
SCRIPT=$(basename "$0" .sh)
VARIANT="${SCRIPT#L2A_Process_}"
SEN2COR_DATA="/opt/sen2cor_data/${VARIANT}"
export SEN2COR_HOME="$SEN2COR_DATA"
export GDAL_DATA="${SEN2COR_DIR}/share/data"

# Fresh prefix
export WINEPREFIX="/tmp/wine_prefix"
export WINEARCH="win64"

# Ensure cfg dir with custom GIPP
if [ ! -f "$SEN2COR_HOME/cfg/L2A_GIPP.xml" ]; then
    mkdir -p "$SEN2COR_HOME/cfg"
    cp "$SEN2COR_DIR/Lib/site-packages/sen2cor/cfg/L2A_GIPP.xml" "$SEN2COR_HOME/cfg/" 2>/dev/null
fi

# DLLs
DLL_DIR="${WINEPREFIX}/dlls"
mkdir -p "$DLL_DIR"
cp -u "$SEN2COR_DIR"/bin/*.dll "$DLL_DIR/" 2>/dev/null
export WINEDLLPATH="Z:\\tmp\\wine_prefix\\dlls"
export WINEPATH="Z:\\opt\\sen2cor-2.12.03\\bin;Z:\\tmp\\wine_prefix\\dlls"

# Headless Wine
cleanup() { [ -n "$XPID" ] && kill "$XPID" 2>/dev/null; }
trap cleanup EXIT
if [ -z "${DISPLAY:-}" ]; then
    Xvfb :99 -screen 0 1024x768x16 &>/dev/null &
    XPID=$!; sleep 0.3
    export DISPLAY=:99
fi

# Init prefix
if [ ! -f "${WINEPREFIX}/drive_c/windows/system32/kernel32.dll" ]; then
    wineboot -u 2>/dev/null; sleep 2
fi

# Parse args
SAFE_PATH=""
OTHER=()
while [ $# -gt 0 ]; do
    case "$1" in
        --output_dir) shift; OTHER+=("--output_dir" "$1") ;;
        --resolution) shift; OTHER+=("--resolution" "$1") ;;
        -*) OTHER+=("$1") ;;
        *)
            if [ -z "$SAFE_PATH" ] && [ -d "$1" ]; then
                SAFE_PATH="$1"
            else
                OTHER+=("$1")
            fi
            ;;
    esac
    shift
done

PYSCRIPT="$SEN2COR_DIR/Lib/site-packages/sen2cor/L2A_Process.py"
PYEXE="$SEN2COR_DIR/bin/python.exe"

if [ -n "$SAFE_PATH" ]; then
    cd "$(dirname "$SAFE_PATH")"
    wine "$PYEXE" -s "$PYSCRIPT" --resolution 10 "${OTHER[@]}" "$(basename "$SAFE_PATH")"
else
    wine "$PYEXE" -s "$PYSCRIPT" "${OTHER[@]}"
fi
RC=$?

echo "--- ${VARIANT} L2A_Process exit: $RC ---"
exit $RC
