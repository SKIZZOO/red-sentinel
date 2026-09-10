# Red Sentinel social signals

Red Sentinel uses one signed server-side endpoint for social notifications:

```text
POST https://red-sentinel.netlify.app/api/webhooks/social
X-Sentinel-Webhook: <your Red Sentinel API token>
Content-Type: application/json
```

Netlify proxies `/api/*` to the Red Sentinel API, so external services can use the HTTPS Netlify URL while the bot remains on the Windows host.

## Routing

In the dashboard, open **Routing** and select a Discord text channel for:

- `twitch`
- `youtube`
- `kick`
- `x`
- `custom`

Routing is stored per Discord server.

## Generic payload

Any worker/automation can send:

```json
{
  "guild_id": "1407973641534177300",
  "provider": "twitch",
  "external_id": "stream-123",
  "title": "Streamer is LIVE",
  "author": "StreamerName",
  "description": "Playing a game",
  "url": "https://twitch.tv/StreamerName",
  "thumbnail": "https://example.com/thumb.jpg"
}
```

The router deduplicates using `(provider, external_id)` in SQLite and sends a Discord embed to the configured provider channel.

## Twitch

Twitch EventSub supports webhook and WebSocket transports. For webhook transport, Twitch requires an HTTPS callback. The Netlify proxy provides the public HTTPS URL:

```text
https://red-sentinel.netlify.app/api/webhooks/social
```

Twitch EventSub itself has a provider-specific signature/challenge protocol. If you use an external worker, have it validate Twitch's EventSub message and then forward the normalized payload above with `X-Sentinel-Webhook`.

## YouTube

YouTube supports push notifications through PubSubHubbub. A small worker can receive the Atom feed notification, normalize the video/channel information, and POST the generic JSON payload to Red Sentinel.

For live-state monitoring, a worker can also use the YouTube Data / Live Streaming APIs and emit a signal when `liveBroadcastContent` becomes `live`.

## Kick and X

Use the same normalized payload from an official API integration or a small polling/webhook worker. Keep provider credentials on the bot host/worker; never put them into the Netlify dashboard bundle.

## Dashboard test

The **Social Feeds** page includes **Send test signal**. This uses the authenticated dashboard session and exercises the real social router and Discord channel routing without requiring a provider account.

## Free/self-hosted setup

You do not need a paid automation service. A small Python/Node worker running on the same Windows PC as Red can call the endpoint directly. Provider APIs may still require their own free developer credentials, quotas, or authorization depending on the provider and feature.
