# SpamClaims Reel 6 ("Storytime"): what to paste into Ads Manager

`ad6/out/spamclaims-reel-storytime.mp4`: 43.9 s, 1080x1920, 24 fps. Cover: `ad6/out/cover-storytime.jpg`.

A Gen Z storytime. Dre, an animated 3D character, tells how he found out that his spam texts could be worth up to $500 each:

1. **The hook.** He's in bed at night when a text lands. He bolts upright: "Okay, storytime. My spam texts? Could be worth up to five hundred bucks. EACH."
2. **The setup.** A sneaker brand (Kixrush, invented) kept texting. He replied STOP, then three more texts came after it.
3. **2 AM.** He looks it up and finds 47 U.S.C. § 227(c)(5), the real text, with "to receive up to $500 in damages for each such violation" highlighted.
4. **The $500 slam.** "Every text after you say STOP? Could be worth up to five hundred dollars." The disclaimer is on screen with the figure.
5. **The skepticism.** "Obviously, I thought it was a scam. So did the group chat." The chat plays out:
   - Marcus: "bro thats a scam 💀"
   - Jay: "no shot"
   - Dre shares the statute: "its literally federal law"
   - Jay: "WAIT its actually real??"
   - Marcus: "i have like 40 of those 😭"
   - Ava: "OH MY GOD"
6. **The answer.** "It's a hundred percent real. A hundred percent legal. For real, for real."
7. **What can count.** "Oh, and it's not just STOP. Texts you never agreed to? Texts after nine PM, like mine? Those can count too. Not every text qualifies, and results vary."
   - The checklist covers the three ways under § 227(c) and its rules:
     - Texts after you said STOP: the opt-out ignored.
     - Texts you never agreed to: no consent, for example to a number on the Do Not Call list.
     - Texts after 9 PM or before 8 AM, your local time (the quiet hours).
   - His 2:06 AM Kixrush text pops in as the receipt: "like mine 💀".
   - Then "2+ texts from the same company", "Not every text qualifies. Results vary." and "Each one that does: up to $500*".
8. **The action.** "Screenshot your texts, and check them free at SpamClaims dot com."
   - The screenshot flashes, then the quick funnel slides in.
   - A tap on "Check my texts" goes to "What did they do?" with picks, a tap on Next to "How many texts" and the "up to $3,000*" meter.
   - It is the same funnel the ad links to.
9. **The close.** "They ignored your STOP. The law didn't." End card: "Spam texts? They could be worth money." / "Each qualifying text: up to $500*" / spamclaims.com / fine print.

## Primary text

storytime: I said STOP. They kept texting. At 2 AM. Turns out there's a federal law for that 👀

If a company sent you 2+ marketing texts after you said STOP, without your consent, or after 9 PM / before 8 AM, the TCPA sets damages of up to $500 per text.* Not every text qualifies, and results vary.

Screenshot your texts and see if they may qualify at SpamClaims.com

*Statutory damages under 47 U.S.C. § 227, not a guarantee. Dramatization: the characters and messages are fictional. SpamClaims is not a law firm and does not provide legal advice.

## Headline (word for word the funnel's first screen and the ad's end card)

Spam texts? They could be worth money.

## Description

See if your texts may qualify

## Call to action button

Learn More

## Website URL

`https://spamclaims.com/lp/quick?vv=reel-storytime&utm_source=instagram&utm_medium=paid_social&utm_campaign=reel_quick&utm_content=reel-storytime`

`/lp/quick` is the quick funnel built for this ad: one tap per card, no dropdowns, the screenshots and three fields.
- It opens on the same headline as the ad's end card.
- It goes live after Publish -> Update in Lovable (spamclaims main `833ca68`).
- Until then, use `/lp/money`.

## Audience

- **Ages 18 to 34.** That is the Gen Z and young-millennial adults the ad speaks to.
- **Never under 18.** A minor can't bring the claim on their own, and Meta restricts this category for teens.
- **Placements:** Reels and Stories on Instagram and Facebook. 7 of 8 partner claims came from Facebook Mobile Reels.

## What it says about the money, and what it doesn't

- **Always "could be worth up to", tied to federal law.** The figure appears with the statute's own words and "not a guarantee; results vary" on screen. "Not every text qualifies, and results vary" is also said out loud.
- **"100% real, 100% legal".** On screen it is "100% REAL" / "100% LEGAL", right after the group chat asks whether the law is real. It means the law is real and checking or claiming is legal. It is not a promise of money.
- **Nobody says they got paid.** Dre's story is finding out that the law is real and checking his texts. None of the friends claims a payout either, so there are no fake testimonials. The "Dramatization" label is on screen at the start and in the fine print.
- **Left out on purpose: "easily make 500 bucks".**
  - It promises an outcome, which Meta rejects as a misleading financial claim (it already disapproved a $500 partner ad).
  - The FTC treats it as deceptive.
  - It isn't true for everyone: most texts won't qualify.
  - The hype is carried instead by the $500 slam, "EACH", the per-text math and the group chat flipping from "scam" to "OH MY GOD".
- **If Meta flags it:**
  - Request a review in Account Quality: "statutory damages information with qualifiers, not a promise of payment."
  - Keep ad 3 cut A (no dollar amount) running alongside.
- **Counsel flag (from the research):**
  - The 7th Circuit (Illinois, Indiana, Wisconsin) and some district courts hold that texts are not "calls" under § 227(c)(5).
  - Consider excluding those states if counsel agrees.

## How it was made, and how to change it

1. **Voice:**
   - `python ad6/voice6.py`: Liam narrates as Dre; Callum, Will and Laura are the friends; all on `eleven_v3` with performance tags.
   - `python ad6/tighten6.py`: TikTok pacing. Pauses are cut and Dre is sped up 1.08x; word and letter timings are kept for captions and lip sync.
2. **Timeline:** `python ad6/edit6.py` writes `ad6/edit.json` (shots, beats, chat, captions).
   - The 3D shots render from it, so patch fields rather than retiming after a render.
3. **Dre in 3D:**
   - `blender/ad6_char.py` builds the character:
     - Designer-toy proportions, the eyes, lids and brows.
     - A mouth decal reshaped every frame for the lip sync.
     - A curly top displaced from a Voronoi texture.
     - A hoodie, and jointed limbs on two-bone IK.
   - `blender/ad6_room.py` builds the bedroom: a velvet channel headboard, a violet LED wash, fairy-light bokeh, posters, and a duvet reshaped per frame.
   - `blender/ad6_scene.py` renders the 7 shots at their place in the ad (`samples=28`, about 15 s a frame).
4. **Screens:**
   - `python ad6/screens6.py`: Dre's phone textures.
   - `node ad6/shoot_lp6.cjs`: `/lp/money` captured with analytics blocked.
   - `node ad6/shoot_statute.cjs`: the federal-law card.
   - The group chat uses the iOS kit's new group mode (`C:\Users\moise\Projects\ios-ui-kit`):
     - iMessage blue, sender names and avatars.
     - Image bubbles, tapbacks and typing dots.
5. **Sound:**
   - `python ad6/sound6.py`: new effects plus the Eleven Music score.
   - The score's drop is placed on the $500 slam using a measured downbeat (`music_full.wav`, offset 6.93 s); it fades out under the last line.
6. **Build:** `python ad6/build6.py` captures (`capture6.cjs` + `ad6.html`), mixes to -15 LUFS and encodes with H.264 at CRF 18.
