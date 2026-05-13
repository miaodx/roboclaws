# Roboclaws command runner.
#
# Public surface:
# - just task::run <task> <driver> [report|profile] [key=value ...]
# - just agent::<dispatcher> ...
#
# Implementation modules stay private so completion shows the composable facade,
# not every lower-level recipe combination. Maintainers can still invoke private
# modules explicitly when debugging.

set dotenv-load := true
set shell := ["bash", "-uc"]

[private]
mod openclaw  'just/openclaw.just'
[private]
mod vlm       'just/vlm.just'
[private]
mod chat      'just/chat.just'
[private]
mod appliance 'just/appliance.just'
[private]
mod dev       'just/dev.just'
[private]
mod mcp       'just/mcp.just'
[private]
mod code      'just/code.just'
[private]
mod harness   'just/harness.just'
[private]
mod verify    'just/verify.just'
[private]
mod molmo     'just/molmo.just'
mod agent     'just/agent.just'
mod task      'just/task.just'

# Default: show the public recipe list.
[private]
default:
    @just --list
