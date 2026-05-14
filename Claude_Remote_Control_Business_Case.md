# Business Case: Enabling Claude Code Remote Control

## What Is Remote Control?

Claude Code's remote control feature lets an authenticated user monitor and interact with an active Claude Code session from a mobile device. The connection is established via a one-time pairing code generated on the originating computer; the session is entirely SSO-based and tied to the user's existing Cars Commerce enterprise credentials.

## Business Case

### Developer Productivity

Long-running agentic tasks (code generation, test suites, data pipelines) routinely take 10–30+ minutes. Remote control allows engineers to:

- **Monitor progress away from their desk** — during lunch, a quick walk, or a meeting — without losing visibility into what the agent is doing.
- **Catch mistakes early** — an engineer can intervene on a running task the moment it diverges, rather than returning to a completed but incorrect result and restarting from scratch.
- **Stay responsive** — time-sensitive agent runs no longer require the engineer to be physically at their machine for the full duration.

These gains compound across a team. A single 20-minute agent run that would otherwise block an engineer at their desk can now run in the background while they reclaim that time.

### Current State

The feature is already enabled by default on the Cars Commerce Claude enterprise account and has been available to the organization for approximately one year. No org-wide policy decision has been required to activate it; it is opt-in at the individual level.

## Security Considerations

| Concern | Mitigation |
|---|---|
| No MDM on employee devices | Sessions are SSO-gated. Revoking SSO immediately terminates all remote sessions. The only residual exposure is the local screen cache on the mobile device, which is equivalent to the exposure from any screenshot. |
| Unauthorized access from a lost/stolen phone | Each remote session requires a fresh one-time pairing code displayed on the originating computer. There is no persistent token on the phone. |
| Session persisting after the computer is locked or closed | Ctrl+C on the originating computer immediately terminates the remote connection. |
| Data leaving the corporate perimeter | Remote control does not transmit code or data to the mobile device beyond what is visible on screen — the same as screen sharing. |

The risk profile is comparable to allowing engineers to screen-share their workstation during a meeting: the session is authenticated, ephemeral, and tied to a revocable SSO identity.

## Recommendation

Continue allowing developers to use remote control on an opt-in basis under the existing SSO controls. No MDM is required because the session lifecycle is fully controlled by the originating workstation and the enterprise SSO provider.

A formal MDM requirement would block a meaningful productivity improvement without meaningfully reducing risk, since SSO revocation already covers the primary threat vector.
