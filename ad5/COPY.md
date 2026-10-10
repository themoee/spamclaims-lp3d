# SpamClaims Reel 5 ("2:13 AM"): what to paste into Ads Manager

`ad5/out/spamclaims-reel-213am.mp4`: 24 s, 1080x1920, 24 fps, a photoreal Blender render. Cover: `ad5/out/cover-213am.jpg`.

The story is one real-looking shot:
1. A dark bedroom at 2:13 AM. The phone wakes up on the walnut nightstand to a spam text and rattles against the wood. Two more texts come in.
2. "You told them STOP. They kept texting." The camera rises over the screen: the conversation shows the STOP, the "you've been unsubscribed" reply, and three more promos after it.
3. "A real company. Two or more texts, weeks after your STOP?" The texts after STOP get numbered 1, 2, 3 with "+20 / +40 / +67 days", and the STOP is circled.
4. "Federal law says each one can mean up to $500 in damages." The $500 card is tied to the statute, with the qualifier on screen.
5. "Results vary, and not every text qualifies." Spoken, and written on the card.
6. "Screenshot your texts, and check them free at SpamClaims dot com." The phone screenshots, then spamclaims.com opens on it.
7. End card: "You said STOP. They kept texting." / "Each text after it: up to $500*" / spamclaims.com / fine print.

## Primary text

You told them STOP. They kept texting.

If a real company sent you two or more marketing texts weeks after your STOP, federal law (the TCPA) sets damages of up to $500 per text.* Results vary, and not every text qualifies.

Screenshot your texts and see if they may qualify at SpamClaims.com.

*Statutory damages under 47 U.S.C. § 227, not a prediction of any recovery. SpamClaims is not a law firm. Not legal advice.

## Headline

You said STOP. They kept texting.

## Description

See if your texts may qualify

## Call to action button

Learn More

## Website URL

`https://spamclaims.com/lp/stop?vv=reel-213am&utm_source=instagram&utm_medium=paid_social&utm_campaign=reel_stop&utm_content=reel-213am`

## About the $500 (Moe asked for it in this one)

Meta disapproved a partner ad that said "Replying STOP could be up to $500" (Financial and Insurance Products). This ad gives the figure its best chance:
- **Situation and criteria first:** the money appears 11 seconds in.
- **Tied to the statute:** "federal law says… up to $500 in damages", with "*Statutory damages under the TCPA, 47 U.S.C. § 227".
- **Qualifier spoken and written:** "Results vary, and not every text qualifies" is on screen for 5 seconds.
- **"Free" kept apart:** it is only in the call to action, 5 seconds after the figure.
- **No cash visuals:** no "get paid", no "claim your $500".

If Meta still rejects it, request a review in Account Quality ("statutory damages information with qualifiers, not a promise of payment"). Keep ad 3 cut A (no dollar amount) running alongside.

## How it was made, and how to change it

1. **Screens:** `python ad5/screens5.py`. The iOS kit renders the 2:13 lock screens, the thread and the evidence versions. spamclaims.com is the ad 3 landing page capture with Safari chrome.
2. **Voice:** `python ad5/voice5.py` (Roger, `eleven_multilingual_v2`); every line is checked by speech-to-text.
3. **Timeline:** `python ad5/edit5.py` writes `ad5/edit.json`; every beat is cued off a word. After a render, patch fields rather than re-running it.
4. **Picture:** `blender -b --factory-startup -P blender/ad5_scene.py -- samples=36`.
   - A walnut nightstand (varnish, pores), the Cosmic Orange iPhone, a braided cable, a glass of water, books, an earbuds case, a linen lamp, the bed.
   - Moonlight through blinds (a spot light and slats) and the screen as the main light.
   - Cycles at 36 samples with denoising; 50-70 mm lenses at f/4-6.3; a little handheld drift. About 14 s a frame.
5. **Look:** `python ad5/post5.py` adds bloom, lateral chromatic aberration, a vignette and grain.
6. **Sound:** `python ad5/sound5.py` makes the room tone, the phone rattling on wood, a soft text tone and the felt-piano score; the pops, tick, shutter and chime are reused from ads 2 and 3.
7. **Build:** `python ad5/build5.py` (post, `capture5.cjs` + `ad5.html`, the mix at -15 LUFS, H.264 CRF 18).
