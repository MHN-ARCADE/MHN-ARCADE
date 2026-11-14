# MHN ARCADE V4 Architecture

## Rust Core

Rust owns:

- Engine domain.
- Session lifecycle.
- Lobby lifecycle.
- Game execution.
- Progression.
- Achievement rules.
- Engine application services.

Rust must not depend on Discord types.

## Python Discord Adapter

Python owns:

- Discord client.
- Slash commands.
- Interactions.
- Views and buttons.
- Embeds and messages.
- Discord events.
- Presentation and localization integration.

Python communicates with Rust through the versioned protocol.

## Process communication

Initial target:

- Rust child process managed by Python.
- JSON Lines over stdin/stdout.
- stdout contains protocol only.
- stderr contains logs.
- Every request has a request_id.
- Protocol version is explicit.
- Requests are serialized in V1.

## Persistence

Storage will be hidden behind repository abstractions.

No V2/V3 database is opened or modified by this bootstrap.

Before migration:

1. Inventory the existing schema.
2. Identify data ownership.
3. Create and verify backups.
4. Design migration and rollback.
5. Test against a copy.

Python and Rust must not independently write
the same data tables.

## Deployment safety

Production FadeHost remains on v3-engine.

Do not deploy this V4 branch until:

- Rust toolchain is verified.
- Child-process support is verified.
- Memory usage is measured.
- Discord adapter is implemented.
- Integration tests pass.
