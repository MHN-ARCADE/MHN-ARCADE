# MHN ARCADE V4

The next-generation MHN ARCADE engine.

V4 is developed independently on the MHN-ARCADE-V4 branch.

## Architecture

- Rust: Discord-independent engine.
- Python: Discord adapter.
- JSON Lines: local process protocol.
- Repository abstractions: persistence boundary.

## Important

V4 is under development.

The production Discord bot must remain on v3-engine.

Do not deploy this branch to the production FadeHost app.

No V2/V3 database migration is included in this foundation.

## Initial checks

Rust:

cargo fmt --manifest-path rust/Cargo.toml --all -- --check

cargo test --manifest-path rust/Cargo.toml --workspace

Python:

python -m compileall -q python main.py

PYTHONPATH=python python -m unittest discover -s python/tests -v
