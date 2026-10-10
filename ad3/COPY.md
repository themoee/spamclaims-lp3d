# SpamClaims Reel 3 ("The 10-second check"): what to paste into Ads Manager

Two cuts of one video, built as an A/B test of the money line. Everything else is identical:

| File | Money line | Length | `vv` tag |
|---|---|---|---|
| `ad3/out/spamclaims-reel-check-a.mp4` | None: "Federal law may entitle you to damages for each one" (the control, safest with Meta review) | 26 s | `reel-check-a` |
| `ad3/out/spamclaims-reel-check-b.mp4` | "Under federal law, damages can be up to $500 per text. Results vary." Spoken and on screen, tied to the statute, after the checklist (the challenger) | 28 s | `reel-check-b` |

Cover: `ad3/out/cover-check.jpg` (the "4 texts after STOP" frame).

The story: a native screen recording of a real iPhone Messages screen, with a creator voice-over (Sarah, ElevenLabs).
1. "You said STOP. They kept texting." The STOP is sent, the brand confirms the opt-out, and four more promos arrive.
2. The 10-second check: open Messages and search "STOP".
3. Tap the company, then count the texts after the STOP. They are numbered 1-4, each labeled "+18 days" and so on.
4. The checklist: 2+ marketing texts from a real company, sent weeks after your STOP, within the last 4 years.
5. Screenshot the STOP and the texts after it. The screenshot drops onto spamclaims.com.
6. End card in the landing page's own look.

## Why it is built this way (the research, Oct 10)

- **No competitor shows how to find the evidence.** Of 105 active TCPA ads from 19 advertisers in the Meta Ad Library, none says "search your Messages for STOP". This ad owns that angle.
- **Our own data says qualification is the leak, not clicks.**
  - Aiden's ads: 379 clicks, 8 claims, only 3 qualified.
  - 5 of the 8 failed on evidence: a single text, rejected screenshots, or claims the screenshots didn't back up.
  - The checklist and "screenshot your STOP and the texts after it" teach what counts before the click.
- **Meta rejected "Replying STOP could be up to $500"** (Financial and Insurance Products policy).
  - Cut A leads with the situation and names no amount.
  - Cut B ties the figure to the statute, says "results vary" out loud, and keeps "free" out of the money line.
- **Native beats polished on Reels.** Meta/Toluna, TikTok and VidMob data favor a real phone screen, sound on, burned-in captions in the middle band, and brand on screen for no more than 25% of the runtime.
- **Message match.** The on-screen hook and the headline are word for word the /lp/stop headline: "You said STOP. They kept texting."

## Primary text, cut A

You told a company STOP. They kept texting?

Here's the 10-second check: open Messages, search "STOP", and count the marketing texts that came after. Two or more, weeks later, from a real company? Federal law may entitle you to damages for each one.

Screenshot your STOP and the texts after it, then see if they may qualify. Free to check, no sign-up.

SpamClaims is not a law firm. Not legal advice. Not every text qualifies; time limits apply.

## Primary text, cut B

You told a company STOP. They kept texting?

Open Messages, search "STOP", and count the marketing texts that came after. Under the TCPA, damages for texts sent after you opt out can be up to $500 per text.* Results vary.

Screenshot your STOP and the texts after it, and see if they may qualify at SpamClaims.com.

*Statutory amount under 47 U.S.C. § 227, not a prediction of any recovery. SpamClaims is not a law firm. Not legal advice.

## Headline (both)

You said STOP. They kept texting.

## Description

- A: Free to check · No sign-up
- B: See if your texts may qualify

## Call to action button

Learn More. Don't use Sign Up: the ad says "no sign-up".

## Website URLs

- A: `https://spamclaims.com/lp/stop?vv=reel-check-a&utm_source=instagram&utm_medium=paid_social&utm_campaign=reel_stop&utm_content=reel-check-a`
- B: `https://spamclaims.com/lp/stop?vv=reel-check-b&utm_source=instagram&utm_medium=paid_social&utm_campaign=reel_stop&utm_content=reel-check-b`

Link straight to spamclaims.com. A redirect domain in the link is one more thing a reviewer can flag. If a partner must use RedTrack, keep their click-id parameter on the link.

## Setup notes

- **Turn off Advantage+ creative enhancements**, including text improvements. Meta turns some on by default, and they can rewrite reviewed copy.
- **Placements:** Facebook and Instagram Reels first; 7 of Aiden's 8 claims came from Facebook Mobile Reels. Stories ads of 16 s or more may be split into separate cards, so a 15 s Stories cut is a separate deliverable if wanted.
- **Judge on cost per qualified claimant, not CTR or cost per lead.** If an ad set can reach about 50 events a week, optimize to a "qualified upload" event (sent through the Conversions API when screenshots pass the gate) rather than Lead.
- **Run A and B in the same ad set with the same budget**, and give each a fixed spend before judging.
- **Counsel check on geography.** On Jul 14, 2026 the 7th Circuit (IL, IN, WI) held that texts are not "calls" under 47 U.S.C. § 227(c)(5). District courts in northern and middle Florida, middle North Carolina and western Virginia have ruled the same way. Ask the partner firms whether to exclude those areas or rely on state law (for example Florida's FTSA) there.

## Wording rules this follows

- Situation first, money second (B) or not at all (A). Never "you'll get", "you're owed" or "claim your $500".
- "May", "can" and "results vary"; the qualifier is spoken as well as shown.
- No cash visuals, no government seals, no "BREAKING".
- The brand (Lumalane) and every number (555-01xx) are invented.
- The end card says SpamClaims is not a law firm.

## How it was made, and how to change it

All of it is HTML and audio: there is no Blender render, so a change takes minutes.

1. **Voice:** `python ad3/voice3.py` (Sarah, `eleven_v3` with a fast-paced tag). Each line is checked by speech-to-text into `ad3/audio/lines.json`. `audition=1` compares candidate voices.
2. **Timeline:** `python ad3/edit3.py` writes `edit_a.json` and `edit_b.json`, with every scene cued off a spoken word. The lines are time-stretched 8% (pitch kept).
3. **Landing page capture:** `node ad3/shoot_lp.cjs` (analytics and database requests are blocked, so it isn't a production visit).
4. **Sound:** `python ad3/sound3.py`. ElevenLabs effects plus the send, receive, shutter and chime sounds from ad 2. Eleven Music makes the beat with a composition plan; the build loops its groove section on bar lines.
5. **Build:** `python ad3/build3.py [cut=a|b]`.
   - `ad3/capture3.cjs` composites `ad3/ad3.html`: the iOS kit runs live in iframes for the real Messages screens, plus the search screen, overlays, captions and end card.
   - It mixes to -15 LUFS with a -1 dBFS ceiling and encodes H.264 at CRF 17.
