# 🛡️ Red Sentinel

<p align="center">
  <b>Discord operations command center for Red-DiscordBot</b><br>
  A modern dashboard for moderation, server management, automation and social alerts.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/license-MIT-purple" />
  <img src="https://img.shields.io/badge/frontend-Netlify-blueviolet" />
  <img src="https://img.shields.io/badge/backend-Red--DiscordBot-red" />
</p>

---

## ✨ Overview

**Red Sentinel** is a self-hosted Discord administration platform built around Red-DiscordBot.
It provides a beautiful web command center where server owners can manage communities, monitor events and connect external social platforms.

The goal is simple:

> Give Discord communities a professional control panel without sacrificing self-hosting and privacy.

---

## 🚀 Features

### 🎛️ Discord Command Center

- Modern dark themed dashboard
- Server selector with persistent sessions
- Server overview and statistics
- Channel management
- Role management
- Server settings panel

### 🛡️ Moderation

- Ban members
- Kick members
- Timeout management
- Message deletion tools
- Audit history
- Discord event logging

### 📡 Livestream Monitoring

Supported platforms:

- Twitch
- YouTube
- Kick
- X / Twitter
- Custom providers

Features:

- Monitor creators automatically
- Send Discord alerts when creators go live
- Custom alert messages
- Custom thumbnails
- Mention everyone option

### 📢 Announcements

- Embed builder
- Rich Discord announcements
- Custom formatting
- Server-wide communication tools

### 🔐 Authentication

- Discord OAuth2 support
- Private API token authentication
- Server-side secret storage

---

## 🏗️ Architecture

```text
                Browser
                   |
                   | HTTPS / JSON
                   |
            Netlify Dashboard
                   |
                   |
          Red Sentinel API
                   |
        +----------+----------+
        |                     |
   Red-DiscordBot          SQLite
        |
 Discord Gateway
        |
 Social Providers
 Twitch / YouTube / Kick / X
```

---

## 📦 Installation

Install the cog:

```text
[p]repo add red-sentinel https://github.com/SKIZZOO/red-sentinel
[p]cog install red-sentinel red_sentinel
[p]load red_sentinel
```

Generate your API token:

```text
[p]sentinel token
```

The token will be sent privately to the command user.

---

## 🌐 Dashboard Setup

The dashboard can be hosted using Netlify or any static hosting provider.

Configure:

- API URL → your Red Sentinel API endpoint
- API Token → generated Sentinel token

For production deployments, Discord OAuth is recommended.

---

## 🔌 Integrations

Red Sentinel uses a provider-neutral webhook system.

Supported routing:

```
twitch  → Discord
youtube → Discord
kick    → Discord
x       → Discord
custom  → Discord
```

---

## 🗺️ Roadmap

- [x] Dashboard foundation
- [x] Discord server management
- [x] Moderation controls
- [x] Livestream monitoring system
- [x] Social routing architecture
- [ ] Advanced analytics
- [ ] Multi-server permissions
- [ ] Plugin marketplace
- [ ] Mobile optimized dashboard

---

## 🤝 Contributing

Contributions are welcome!

You can help by:

- Reporting bugs
- Suggesting features
- Improving documentation
- Creating pull requests

Before contributing, please read the contribution guidelines.

---

## 💜 Thanks

Special thanks to:

- The Red-DiscordBot community
- Discord developer community
- Open-source contributors
- Everyone testing and improving Red Sentinel

---

## 📜 License

Red Sentinel is released under the **MIT License**.

You are free to:

✅ Use it

✅ Modify it

✅ Share it

✅ Build upon it

See `LICENSE` for details.

---

<p align="center">
Built with ❤️ for Discord communities.
</p>
