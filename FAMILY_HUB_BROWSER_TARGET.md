# Samsung Family Hub browser target

This app is served to a Samsung Bespoke **RF29BB8900JMAP** refrigerator.
Treat it as a web page for an embedded appliance browser, not as an Android app.

## Target

- Physical display: 21.5-inch touch screen, **1920 x 1080** (Full HD).
- Software family: Family Hub 7.0 on Tizen. Firmware varies by region and OTA update.
- Browser: the built-in Samsung Internet browser. It cannot be replaced and does not support browser plugins.
- Field reports from Family Hub show a Chromium 108 / SamsungBrowser 1.0 user agent. Use ordinary HTML, CSS, and JavaScript; test advanced browser features on the physical refrigerator.
- `1920 x 1080` is the display, not a guaranteed page viewport. Browser chrome and fullscreen state change `window.innerWidth` and `window.innerHeight`; use responsive layout and never hard-code the viewport size.

## Implementation rules

- Keep the UI small and dependency-light. Do not require an Android APK, a Tizen app install, a service worker, or a kiosk/fullscreen mode.
- Start audio only from a user gesture. Preserve the selected track and playback state so the page can recover after a browser restart.
- Do not assume timers, WebSocket events, polling, or rendering continue while the screen sleeps.
- On `visibilitychange`, `pageshow`, and `focus`, run an idempotent `sync()` that refreshes remote state and reconnects any live transport. Do not automatically restart audio if the browser rejects autoplay.

## Screensaver / wake-up constraint

Family Hub enters its screensaver after its configured display timeout; do not assume a five-minute delay. Community reports show that its browser may freeze the page while asleep: on wake, UI data can be stale because events received during sleep were not rendered. Fullscreen mode can also be lost after wake.

Design wake-up as a recovery path, not as normal continuous execution: re-fetch state, reconcile the UI, and make every operation safe to repeat. Test at least one full screensaver cycle using the refrigerator's current timeout, a network reconnect, and reopening the browser on the real refrigerator.

### Observed Cover screen behavior

The refrigerator calls this feature **Cover screen**. During physical-device testing it was enabled with these settings:

- **Cover screen start after:** 15 seconds.
- **Cover screen duration:** 2 minutes. The settings UI allows a duration of up to 2 hours.

When a song finishes after the refrigerator has been left untouched, the display does not visibly enter Cover screen. Instead, it turns off immediately. The first tap wakes the display into Cover screen; a second tap returns to the Internet browser.

This suggests that audio playback may postpone showing Cover screen without resetting its duration timer. By the time playback stops, the refrigerator may consider the Cover screen duration already expired and turn off the display immediately. This is a field hypothesis, not confirmed Samsung behavior.

Turning the display off freezes or interrupts browser audio before the next track can start reliably. The following client-side experiments did not prevent it and were reverted:

- requesting a Screen Wake Lock during continuous playback;
- overlapping two audio elements for 3 seconds;
- replacing the source of one audio element about 1 second before the track ended.

A future physical-device test should increase **Cover screen duration** to 2 hours while using the baseline player. If playback continues between tracks under that setting, the display-off deadline, rather than entry into Cover screen, is the likely cause of the interruption.

## References

- Samsung's [Family Hub 7.0 model list](https://www.samsung.com/us/support/answer/ANS10002430/)
- Samsung's [app-installation restriction](https://www.samsung.com/us/support/answer/ANS10006847/)
- Family Hub [screensaver freeze report](https://community.sharptools.io/t/samsung-family-hub-dashboard-not-refreshed/14668)
