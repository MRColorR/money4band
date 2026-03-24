# Notifications

> Get alerts when your stack starts, stops, errors, or has updates.

---

## Overview

M4B uses [Shoutrrr](https://containrrr.dev/shoutrrr/) to send fire-and-forget notifications through **19 supported services** including Discord, Telegram, Slack, Email, and more.

## Setup

From the interactive menu, choose the notification setup option, or configure directly in `user-config.json`:

```json
{
  "notifications": {
    "enabled": true,
    "url": "discord://token@webhook-id",
    "events": {
      "stack_start": true,
      "stack_stop": true,
      "stack_error": true,
      "update_available": true
    }
  }
}
```

## Supported Events

| Event | Trigger |
|-------|---------|
| `stack_start` | Docker Compose stack started successfully |
| `stack_stop` | Stack stopped |
| `stack_error` | Stack operation failed |
| `update_available` | New M4B version detected |
| `test` | Manual test notification |

## Testing

```bash
m4b notify test
```

## Shoutrrr URL Examples

| Service | URL Format |
|---------|-----------|
| Discord | `discord://token@webhook-id` |
| Telegram | `telegram://token@telegram?channels=channel-id` |
| Slack | `slack://hook:token-a/token-b/token-c` |
| Email (SMTP) | `smtp://user:password@host:port/?to=recipient` |
| Gotify | `gotify://host/token` |
| Pushover | `pushover://shoutrrr:token@user/` |

See the [Shoutrrr docs](https://containrrr.dev/shoutrrr/services/overview/) for all 19 services.

## How It Works

Notifications are sent via a temporary `containrrr/shoutrrr` Docker container — no additional dependencies to install. The container runs, sends the message, and is automatically removed.
