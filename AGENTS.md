# Omni agent entry point

For simulator or device UI work, read [docs/UI_AGENT_HANDOFF.md](docs/UI_AGENT_HANDOFF.md) first. It contains the current product behavior, source map, simulator and Pi commands, speech/Gemini configuration, testing, deployment, profile synchronization, and troubleshooting.

The active simulator is pygame and shares its UI with the Pi through `firmware/native_ui.py`. Do not implement current UI changes in the archived `eink-preview/` browser prototype or old e-ink firmware.

Preserve the established behavior documented in the handoff unless the user asks to change it. Edit and test locally first. A request to test on the Pi does not itself mean publish to GitHub; the Pi uses SCP deployment and does not require Git. Follow the user's current instructions about committing, pushing, and deploying.

Keep `.env` and credentials, downloaded speech models, machine profiles, build output, and deployment manifests out of commits. The untracked `eink-preview/` and `firmware/.pio/` directories predate this handoff; preserve them and exclude them from normal staging/deployment.
