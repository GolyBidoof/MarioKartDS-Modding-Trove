#!/usr/bin/env python3
"""Example scenario for debug/recomp/client/run_scenario.py.

Run with:
    python3 debug/recomp/client/run_scenario.py --binary ./build/game \
        debug/recomp/examples/scenario_example.py
"""
import os

from dbg_client import Debugger


def main():
    debugger = Debugger(port=int(os.environ["DBG_PORT"]))
    try:
        debugger.pause()
        print(debugger.status())

        debugger.snapshot("boot")
        debugger.screenshot_both("dbg_both_native.bmp")    # 256x384
        debugger.screenshot_upper("dbg_upper_native.bmp")  # 256x192
        debugger.screenshot_lower("dbg_lower_native.bmp")  # 256x192
        debugger.screenshot_full("dbg_both_full.bmp")      # keep the full frame

        debugger.resume()
        debugger.wait(60)
        print(debugger.status())
        print(debugger.diff("boot"))
    finally:
        debugger.close()


if __name__ == "__main__":
    main()
