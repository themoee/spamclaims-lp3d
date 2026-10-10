# SpamClaims Reel: what to paste into Ads Manager

Two 15-second, 1080x1920 cuts of the same video, for a hook test:

| File | Hook (first 3 s) | `vv` tag |
|---|---|---|
| `spamclaims-reel-15s.mp4` | "Still getting spam texts after you said STOP?" ($500 lands at 10 s) | `reel-story` |
| `spamclaims-reel-15s_b.mp4` | "Got texts after STOP? Each one could be worth up to $500*" | `reel-money` |

Placements: Instagram Reels and Stories (also fine for Facebook Reels). Both files are under 15 s, so Stories
show them as one card.

## Primary text

Replied STOP and they kept texting? Under federal law, each text after STOP could be worth up to $500.*
Upload your screenshots and see if your texts may qualify. Free to check, no sign-up.

*Statutory damages under the TCPA, per violating text. Not a guarantee; results vary. Not legal advice.

## Headline

Texts after STOP? See if they qualify

## Description

Free to check · No sign-up

## Call to action button

Learn More

## Website URLs (each version reports separately in Admin → Landing pages)

- Version A: `https://spamclaims.com/lp/stop?vv=reel-story&utm_source=instagram&utm_medium=paid_social&utm_campaign=reel_stop&utm_content=reel-story`
- Version B: `https://spamclaims.com/lp/stop?vv=reel-money&utm_source=instagram&utm_medium=paid_social&utm_campaign=reel_stop&utm_content=reel-money`

If the ad runs through a partner or RedTrack, keep their click-id parameter on the link as well (see the
advisor's tracking-path notes).

## Wording rules this follows

- "could be worth up to $500" and "may qualify", never "you'll get" or "you're owed".
- The asterisk and the TCPA fine print sit on the end card and in the primary text.
- No attorney names, no case results, no settlement numbers.

## How it was made, and how to change it

- Voice: ElevenLabs "Eric - Smooth, Trustworthy" (`eleven_multilingual_v2`), both versions. Another voice:
  `python ad/voice.py voice=Chris` (and `edit=edit_b.json` for version B), then `python ad/build.py`.
- Sound effects: ElevenLabs text-to-sound-effects (`python ad/voice.py voice=Eric sfx=1`), placed on the story's
  beats by `ad/sfx.py`. Music: Eleven Music, tension to the 9.4 s cut (`ad/music.py`) and a sustained lift after it
  (`ad/music_outro.py`). Mix: about -15 LUFS, peaks at -1 dBFS.
- Captions appear when their words are spoken (`ad/sync.py`, from the voice's word timestamps).
- Picture: `blender/story.py` with `tfile=../ad/edit.json adcam=1` at 1080x1920; change the shots in `ad/edit.py`.
