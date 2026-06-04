# Elite Dangerous — Early Warning System (EWS)

Early detection of Thargoid hyperdictions during hyperspace jumps.

## Features
- Detects hyperdictions before visual shaking starts.
- Works with plotted routes (SRS) and blind jumps.
- Uses `SystemAddress` comparison for reliability.
- 60-second network lag protection.
- Plays warning sounds (unstable.ogg, dropped.ogg).

## Installation
```bash
git clone https://github.com/yourname/EliteDangerous-EWS.git
cd EliteDangerous-EWS
pip install -r requirements.txt
