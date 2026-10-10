# SpamClaims Reel 2 ("Did you mean START?"): what to paste into Ads Manager

One 24-second, 1080x1920 video: `ad2/out/spamclaims-reel-start.mp4` (cover: `ad2/out/cover.jpg`).

The story: you reply STOP to a cookie brand five times, more desperate each time ("Me, politely", "Me, louder",
"Me, unwell"), they keep texting (at 2 AM, too), then reply "Did you mean START?". Record scratch, plot twist: every
text after your first STOP could be worth up to $500.* The phone spins, the screenshot is taken, the texts after STOP
light up, and the end card points to spamclaims.com.

Placements: Instagram Reels and Stories (also fine for Facebook Reels). Stories ads play up to 60 s as one card.
The money line and the newest texts stay above y = 1250 px, clear of the Reels caption and buttons.

## Primary text

You said STOP. They said "Did you mean START?"

Plot twist: under federal law, each text after your first STOP could be worth up to $500.* Upload your
screenshots and see if yours may qualify. Free to check, no sign-up.

*Statutory damages under the TCPA, per violating text. Not a guarantee; results vary. Not legal advice.

## Headline

Said STOP? Your spam could pay off

## Description

Free to check · No sign-up

## Call to action button

Learn More

## Website URL (reports separately in Admin → Landing pages)

`https://spamclaims.com/lp/stop?vv=reel-start&utm_source=instagram&utm_medium=paid_social&utm_campaign=reel_stop&utm_content=reel-start`

If the ad runs through a partner or RedTrack, keep their click-id parameter on the link as well.

## Wording rules this follows

- "could be worth up to $500" and "may qualify", never "you'll get" or "you're owed".
- The asterisk and the TCPA fine print sit on the end card and in the primary text.
- The brand (CrumbClub) and the number (+1 877 555-0134) are invented; 555 numbers are fictional.
- No attorney names, no case results, no settlement numbers, no Apple names or logos.

## How it was made, and how to change it

Every step reads `ad2/edit.json`, the timeline. Re-running `edit2.py` retimes everything from the voice
lengths, and the Blender frames must then be rendered again, so for small changes patch the field in edit.json.

1. Voices (`python ad2/voice2.py`): ElevenLabs. "Me" is Chris (`eleven_v3`, performed with audio tags:
   politely, annoyed, shouting, desperately, calmly unhinged), the brand is Jessica (`eleven_v3`, cheerful and
   sweet), the narrator is Brian (`eleven_multilingual_v2`). Each line is checked by speech-to-text
   (`ad2/audio/lines.json`).
2. Phone screens (`python ad2/states.py`): the iOS kit renders the conversation one message at a time, scrolled
   so the newest text stays high on the screen.
3. Timeline (`python ad2/edit2.py`): beats, stickers, the reveal and the end card from the voice timings.
4. Sound (`python ad2/sound2.py`, `python ad2/music2.py`): ElevenLabs sound effects for every beat (drop, landing,
   sent and received texts, 2 AM crickets, record scratch, spin, shutter, coins, cha-ching, logo jingle) and Eleven
   Music: a comedy groove that the record scratch stops dead, then a payoff groove (composition plan) that drops on
   the screenshot flash and ends on its final chord.
5. Picture (`blender -b --factory-startup -P blender/ad2_scene.py`): the deep blue phone, Cycles on the GPU,
   transparent background, about 9 s a frame (733 frames, about 1 h 50 min).
6. Build (`python ad2/build2.py`): `ad2/capture2.cjs` composites `ad2/ad2.html` (sunset background that heats up
   with each STOP, the 2 AM night beat, stickers, money card, coins, end card) over the frames; the mix puts each
   spoken STOP on its bubble (vowel onset, not the s-hiss), ducks the music under the voices, and lands at
   -15 LUFS with a -1 dBFS ceiling; ffmpeg encodes H.264 high, CRF 17, AAC 192k.
