# Retired Maintainer Local Notes

This page is historical. It is kept only so old links and retrospectives have a
landing page.

Current household runs use the public command surface documented in the root
`README.md` and `just/README.md`. Guarded maintainer engines are not part of the
normal public engine list and should not be used as current run guidance unless
a fresh plan explicitly reopens that route.

Use `just dev::network-status` before any guarded maintainer workflow. If it
reports `network: work`, do not run that workflow from that network.
