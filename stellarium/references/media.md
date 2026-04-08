# Media

Use this reference when the user wants Stellarium to play audio or video.

## Practical Guidance

- Media support may depend on the current Stellarium build and backend.
- A documented engine class does not guarantee identical script exposure.
- Test media support with a tiny probe before building a larger workflow.

## Working Pattern

1. Create a small local media probe.
2. Run it through direct script execution or a local `.ssc` file.
3. Confirm success by observing:
   - visible probe labels
   - advancing playback position or duration
   - audible output

## Current Design Advice

- Prefer explicit probe scripts for media.
- For audio-only playback, test what the script environment supports.
- If direct audio APIs are unavailable, a video manager may still play media-backed audio depending on the build.

Keep media behavior documented as empirical unless it has been verified on the current running instance.
