# Ejection checklist for kt-turtlebot3-host

Eject/self-contained packaging is a future explicit flow, not a normal `ktm project pack` mode today.

## Current expectation

- [ ] `ktm project pack` succeeds without vendoring dependency closure.
- [ ] The retained `compiled-source` policy does not vendor dependency closure; v2 does not expose a mode-selection flag.
- [ ] Eject/self-contained packaging remains unavailable; do not vendor dependencies manually.
- [ ] Normal archives do not contain `deps/`, `.ktrees/`, KTM store paths, managed interpreters, dependency wheels, or `libkt` libraries.

## SDK-specific risk

Python runtime source is packaged as the app artifact; ejecting would additionally
vendor managed Python, SDK and Messages wheels, native `libkt` dependencies, and
their licenses, which is not part of source or compiled-source mode.

## Before any future eject implementation

- [ ] Make eject an explicit command or mode with clear UX; do not silently overload `compiled-source`.
- [ ] Copy the full dependency closure deterministically into an owned payload root such as `deps/`.
- [ ] Include license notices and SBOM/provenance evidence for vendored dependencies.
- [ ] Document who owns security updates after ejection.
- [ ] Re-run native link audit against the self-contained closure.
- [ ] Add release tests proving normal modes remain KTM-managed while eject mode vendors only the intended closure.
