# Roboclaws command runner.
#
# Run `just` (or `just --list`) to see all recipes grouped by module.
# Run `just <module>` to see one module (e.g. `just openclaw`).
#
# Modules live in `just/<name>.just`. Each is self-contained — delete the file
# to remove a whole family of recipes, no edits elsewhere required.
#
# Adding a module: create `just/<name>.just` and append `mod <name>` below.

set dotenv-load := true
set shell := ["bash", "-uc"]

mod openclaw  'just/openclaw.just'
mod vlm       'just/vlm.just'
mod chat      'just/chat.just'
mod appliance 'just/appliance.just'
mod dev       'just/dev.just'
mod mcp       'just/mcp.just'
mod code      'just/code.just'
mod harness   'just/harness.just'
mod verify    'just/verify.just'

# Default: show the grouped recipe list.
default:
    @just --list
