# WSL Compatibility Note

WSL is no longer the assumed target environment. The Idun fork uses the same
native C++17 build on Alpine, Debian, Ubuntu, and WSL.

See [setup_linux.md](setup_linux.md) and run:

```sh
bash tools/setup_linux.sh
make all
```

No adjacent CP/M-65 or UDOS checkout is required.
