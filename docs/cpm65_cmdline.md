# Retired CP/M Command-Line Notes

The CP/M-era command-line runner path is no longer maintained.

Current command flow under UDOS:

- `ACTC <MODULE>` writes `OBJ/<MODULE>.OBJ`
- `ALINK <MODULE>` writes `BIN/<MODULE>.PRG`
- UDOS launches the linked PRG directly
