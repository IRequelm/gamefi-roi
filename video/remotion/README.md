# Remotion video

<p align="center">
  <a href="https://github.com/remotion-dev/logo">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://github.com/remotion-dev/logo/raw/main/animated-logo-banner-dark.apng">
      <img alt="Animated Remotion Logo" src="https://github.com/remotion-dev/logo/raw/main/animated-logo-banner-light.gif">
    </picture>
  </a>
</p>

This is GamCryp's production motion renderer for evidence-led vertical Shorts. It
replaces the old FFmpeg card stack with six animated scenes whose primary visual
is official source media: an official product/game video when available, or an
official product/site capture when it is not. Remotion adds crop, pan, highlights,
source attribution, source-bound captions, and an optional local brand sting; it
does not fabricate gameplay or a fake UI.

## Commands

**Install Dependencies**

```console
npm i
```

**Start Preview**

```console
npm run dev
```

**Render video**

```console
node scripts/render-pilot.mjs
```

The integrated Python renderer uses the same composition automatically for
`SHORT_FORM` packages. Official video files under
`data/local/video_assets/<opportunity>/` are preferred over still captures. It
writes review-only output to
`data/local/video_render/short/`; it never calls ElevenLabs and never publishes.

Preview the composition with:

```console
npm run dev -- --no-open
```

**Upgrade Remotion**

```console
npx remotion upgrade
```

## Docs

Get started with Remotion by reading the [fundamentals page](https://www.remotion.dev/docs/the-fundamentals).

## Help

We provide help on our [Discord server](https://discord.gg/6VzzNDwUwV).

## Issues

Found an issue with Remotion? [File an issue here](https://github.com/remotion-dev/remotion/issues/new).

## License

Note that for some entities a company license is needed. [Read the terms here](https://github.com/remotion-dev/remotion/blob/main/LICENSE.md).
