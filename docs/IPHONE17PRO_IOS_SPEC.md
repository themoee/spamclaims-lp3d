# iPhone 17 Pro + iOS Messages: the measured spec

Every number here was measured or confirmed on 2026-10-09 from: Apple's iPhone 17 Pro tech specs
(support.apple.com/en-us/125090), Apple Newsroom press images (Sept 9, 2025 launch), and a real iOS
screenshot of a spam conversation taken on an iPhone on 2026-10-02 (921×2000, Display P3 pixels).
Anything marked "est." is an informed estimate; everything else is measured.

Legal guardrails for every asset built from this spec:
- No Apple logo anywhere (the back glass panel is plain). Never write "iPhone" or "Apple" on the page.
- No SF Pro / SF Symbols files: they are licensed for Apple-platform mockups only. Use **Inter** (OFL)
  as the font (closest open match) and draw every icon as our own simple SVG/canvas paths.
- No Apple wallpapers. Use our own abstract wallpaper.
- Sender numbers use the fictional 555-01XX range; brands are invented.

---------------------------------------------------------------------------------------------------
## 1. Hardware (iPhone 17 Pro, not Pro Max)

| Item | Value | Source |
|---|---|---|
| Height × width × depth | 150.0 × 71.9 × 8.75 mm (depth excludes the camera plateau) | Apple tech specs |
| Weight | 206 g | Apple tech specs |
| Frame / body | aluminum unibody (heat-forged), flat sides, softly rounded edges | Apple |
| Front | Ceramic Shield 2 (flat glass) | Apple |
| Back | Ceramic Shield glass panel in an aluminum surround, below the camera plateau | Apple |
| Colors | **Cosmic Orange**, **Deep Blue**, **Silver** | Apple |
| Display | 6.3" OLED, 2622 × 1206 px, 460 ppi = **402 × 874 pt @3x**; active area ≈ 144.8 × 66.6 mm | Apple + math |
| Screen inset from body edge | ≈ 2.65 mm each side (measured 2.9 mm incl. anti-aliasing) | press photo |
| Polished outer rim seen from the front | ≈ 1.3 mm, then ≈ 1.1 mm black border, then the screen | press photo |
| Body corner radius (front outline) | ≈ 13.0 mm, continuous-curvature corner (fits a 14 mm circle) | press photo fit |
| Screen corner radius | **62 pt ≈ 10.3 mm** (concentric with the body) | community value, consistent with the fit |
| Dynamic Island | **126 × 37.33 pt** pill (≈ 20.9 × 6.2 mm), top edge **11 pt** below the screen top, centered | press photo (20.9 mm) |
| Left side (front view) | Action button ≈ 29.7–35.4 mm from top; volume up ≈ 42.5–51 mm; volume down ≈ 55.8–64.2 mm | press photo |
| Right side | side button ≈ 45–59 mm from top; **Camera Control** (flush sapphire, slightly darker) ≈ 90–107 mm (est.) | press photo / est. |
| Bottom | USB-C port centered (≈ 9 × 3.2 mm stadium); a row of 6–7 round grille holes left and right | est. |
| Buttons | ≈ 0.5 mm proud of the side, 2.6 mm tall (front-back), rounded | est. |

### Back layout (measured by pixel analysis of Apple's straight-on Cosmic Orange back photo; origin = top-left of the back as you look at it, x right, y down, mm)
- **Camera plateau**: full width (0–71.9 mm), from the top edge down to **y ≈ 43.5 mm** (29 % of the height;
  the step and its fillets read as a dark line at 43.1 and a highlight at 44.2). Its top corners follow the body
  corners; its two lower corners are rounded (≈ 7 mm est.). It stands ≈ 1.9 mm proud of the back (est.), with a
  softly radiused outer edge and a small fillet at its base. Same aluminum as the body. The antennas run around
  the plateau's perimeter (a fine line at the step is plausible; keep it subtle).
- **Three lenses**: dark cover glass **Ø 14.0 mm**, color-matched polished ring to **Ø ≈ 16.4 mm** outer, ≈ 1.2 mm proud
  of the plateau; centers top-left **(14.4, 14.0)**, bottom-left **(14.3, 33.4)**, middle-right **(32.5, 23.7)**.
  The bottom lens ring sits only ≈ 1.4 mm above the plateau edge (measured), the top one ≈ 5.8 mm below the top.
- **Flash** (frosted warm-white disc, Ø ≈ 7 mm): **(57.5, 14.0)**. **Microphone** hole (Ø ≈ 1.2 mm): **(57.5, 23.7)**.
  **LiDAR** (black glass disc, Ø ≈ 7 mm): **(57.5, 33.4)**. The right column mirrors the left lens column; the three
  rows line up with the lens rows. (Mirror x for front-view coordinates: x_front = 71.9 − x_back.)
- **Ceramic Shield glass panel**: x **3.9 → 68.0 mm**, y **48.5 → 146.5 mm** (measured); rounded corners ≈ 9.4 mm,
  concentric with the body; flush with the aluminum, a satin/frosted finish, slightly lighter than the metal;
  a strip of bare aluminum (≈ 4.5 mm) between the plateau step and the panel.

### Color references (sRGB, sampled from Apple's studio photos; use as albedo starting points, tune by eye)
| Finish | highlight | mid | shadow |
|---|---|---|---|
| Cosmic Orange metal | #FB9461 | #D97A42 | #D15F30 |
| Cosmic Orange glass panel | #E28246 | #D47035 | — |
| Deep Blue | #4A5876 | #2B3548 | #1C2333 |
| Silver | #F0F0EE | #D8D8D6 | #A9A9A7 |
Lens rings: polished, color-matched to the finish (orange rings on Cosmic Orange).

---------------------------------------------------------------------------------------------------
## 2. iOS Messages UI (the current Liquid Glass design)

Canvas **402 × 874 pt**, rendered at **3× = 1206 × 2622 px** for textures. All values in pt.
Re-measured 2026-10-09 against the reference screenshot with `ios-ui-kit/verify/compare.py` (sub-pixel edges;
every box within 2.4 %, fills within ΔE2000 0.8; see `C:\Users\moise\Projects\ios-ui-kit\VERIFY.md`).
**The reference was taken at Dynamic Type xLarge** (body 19 pt, caption 14 pt; the status-bar clock is fixed at
17 pt), so text-related values are given as *default (Large) / reference (xLarge)*; text-related spacing scales by
body size / 19. Non-text controls (status bar, back button, avatar, "+", margins) do not scale.

### Colors (sRGB; the reference screenshot's pixels are Display P3 and were converted)
| Element | Dark mode | Light mode |
|---|---|---|
| Background | `#000000` | `#FFFFFF` |
| Received bubble | `#262628` (measured) | `#E9E9EB` |
| Received text | `#FFFFFF` | `#000000` |
| Sent SMS bubble (green) | `#30D158` (measured, P3 → sRGB; ΔE 0.35) | `#34C759` |
| Sent iMessage (not used) | `#0A84FF` | `#007AFF` |
| Sent text | `#FFFFFF` | `#FFFFFF` |
| Timestamps, "Text Message • SMS" | `#8E8E90` (measured mode rgb 142,142,144) | `#8E8E93` |
| Back button, name capsule, compose field (glass) | white 12 % over the content (lum 31 over black), backdrop blur ≤ 1 pt (text behind stays legible), rim bright only along the top and bottom (+25 to +69 lum), none at the sides | `rgba(255,255,255,0.72)` + blur, hairline `rgba(0,0,0,0.06)`, soft shadow |
| "+" button | near-opaque `rgb(61,61,64)` (lum 61 over black and over a bubble alike) | `rgba(255,255,255,0.8)` + shadow |
| Placeholder / waveform / capsule chevron | white 45 % / 33.5 % / 22 % over the glass | `rgba(60,60,67,0.45)` |
On wide-gamut browsers the green may be emitted as `color(display-p3 0.4157 0.8118 0.4118)` (dark) for an exact match.

### Typography (Inter as the SF Pro stand-in; px = pt)
| Use | SF size default / ref | Inter (default / ref) | Weight | Tracking / notes |
|---|---|---|---|---|
| Bubble text | 17 / 19 | 16.8 / 18.8 px, line pitch **19.7 / 22.0** (1.16 em, not the design table's 22 at 17) | 400 | 0 (Inter's own spacing reproduces every SF line break of the reference) |
| Timestamp header ("**Today** 5:04 AM") | 12 / 14 | 11.5 / 13.4 px | day 600, time 400 | +0.15 / +0.18 px; **narrow no-break space U+202F before AM/PM** |
| "Text Message • SMS" line | 12 / 14 | 11.5 / 13.4 px | 600 | +0.15 / +0.18 px; second line = the date, styled like a timestamp |
| Status-bar time | 17 (fixed) | 16.15 px, digits 11.75 tall | 600 | +0.64 px |
| Header name pill | 17 / 19 | 16.9 / 18.9 px | 600 | +0.67 / +0.75 px; tabular figures except "1" (SF's digits are wide) |
| Compose placeholder | 17 / 19 | 16.4 / 18.3 px | 400 | 0 |
| Lock-screen date | 21 | 20.4 px | 600 | 0 |
| Notification title / body | 15 / 20 | 15 / 20 px | 600 / 400 | −0.1 px |
The phone blends text in linear light, so its light-on-dark text carries ~20 % more ink than a browser's grayscale
antialiasing. PNG textures add a same-color 0.2–0.4 pt text stroke in dark mode (no change to advance widths).

### Layout (measured on the reference; default / reference where they differ)
- **Status bar**: time centered on x 53.25, digit center y 29.9 (baseline 35.7), vertically centered on the island.
  Right side: 4-bar cellular (bars 3.35 wide, pitch 5.45, heights 6.4 / 8.5 / 10.6 / 12.7, bottoms at y 35.6, from
  x 296), 3-segment Wi-Fi (17.9 × 13.55 at x 322.6, y 22.7), battery body 26.2 × 13.55 (radius 4.3) at x 347, y 22.7,
  nub 1.7 × 4.4; full, no percentage. Silent mode adds a bell-slash at x 76–89.
- **Dynamic Island**: black pill 126 × 37.33 at y = 11, centered (drawn in every texture).
- **Header** (glass, floats over content): back button = glass circle Ø 40.2 at x 18.33, y 56.4 (center y 76.5),
  chevron 14 × 23 with a 3.3 stroke, round caps; avatar Ø 54.5 centered (201, 84.1), gradient `#55526A → #2F2A4C`
  dark / `#C7C7CC → #A9A9B0` light, white person glyph (head 20 × 20.6 at center y 77.6, lens-shaped shoulders
  34.5 wide); the avatar is drawn over the name capsule. Name capsule: top y 106.8 (overlaps the avatar by 4.6),
  height **30.5 / 34.1**, stadium; left pad 10.0 / 11.2, name, 5.5 / 6.1 gap, chevron "›" 5.7 × 14, right pad 8.8 / 9.8.
- **Content**: side margins **18.33**. Natural top: first header line's baseline 21.5 / 24 below the name capsule.
  Content scrolling under the header fades out (dark gradient from the top to y ≈ 150).
- **Bubbles**: padding **11.7 h × 8.5 v / 13.05 × 9.5**; one-line height **36.7 / 41.0**; corner radius **18.3 / 20.5**
  (= half a one-line bubble, so one-line bubbles are stadiums); widest text line **258.3 / 255.5** (fit test excludes
  a trailing space). Width = widest line + 2 × padding, where a line that wrapped at a space keeps that space
  (so a full bubble can reach 284 at xLarge). URLs may break after `//` or `/`, words after a hyphen.
  **Tail** on the LAST bubble of a run only (received bottom-left, sent bottom-right, mirrored): the corner arc
  turns straight down 3.5 above the bottom, runs at 10.5 in from the outer edge, curls out to 8.3 and ends in a
  rounded point 7.0 below the bubble, 9.7 in from the edge; its inner edge rises back to the bubble bottom at ~25
  (values at xLarge; scale by 17/19 for default). Spacing: same run **1.8 / 2**, new sender run **12.8 / 14.3**
  (bubble bottom to next top), timestamp: previous bubble bottom → timestamp baseline **41.5 / 46.4**, baseline →
  next bubble top **12.8 / 14.3**; a header's two lines are 18.0 / 20.1 apart.
- **Links** inside received bubbles from an **unknown sender are plain text** (no underline, no preview), as on the
  reference; underlined in the text color only once links are active (known sender).
- **SMS**: no "Delivered"/"Read" receipt under sent bubbles. Header text is "Text Message • SMS" + date line.
- **Timestamp grouping**: a new header when > 60 min since the previous message. Format: "Today 9:12 AM",
  "Yesterday 9:12 AM", weekday within 6 days ("Tuesday 3:01 PM"), else "Mon, Sep 1 at 3:01 PM" (day part bold).
- **Compose bar**: "+" circle Ø 36.7 at x 18.1 (near-opaque glass, white "+" 14.4 with a 1.6 stroke); field from
  x 65.5 to 383.4, height **39.2 / 41.5**, both centered on the same line; placeholder "Text Message • SMS" 15.7 in
  from the field's left; waveform glyph centered at x 364.6 (5 rounded bars 1.9 wide, pitch 3.6, heights 3.6 / 7.1 /
  14.8 / 7.1 / 3.6). Without the keyboard the field's bottom sits at y ≈ 832 (not on the reference: it shows the
  keyboard, with the field's bottom at 542.1).
- **Home indicator**: 134 × 5 pill, radius 2.5, centered, bottom 8; white @ 70 % (dark) / black @ 85 % (light).

### Lock screen (for the "texts keep arriving" scene)
- Our own wallpaper (brand gradient: deep navy `#0B1226` → `#1F2A4D` with an orange glow `#F58220` low right).
- Status bar right side as above, no clock on the left; a small padlock centered just below the island (y 55–72).
- Date "Thursday, September 18" (21, 600) with its cap center at y ≈ 96; clock "9:41": light Inter Display
  (weight 330, opsz 32, 116 px) stretched 1.42× vertically → digits ≈ 120 pt tall, frosted fill (white 96 % at the
  top to 72 % at the bottom), digit center at y ≈ 175.
- Notifications stack from the bottom up (newest on top of the stack), the lowest one ending at y 752, 8 apart:
  platter = width 402 − 2×12, radius 24, glass (dark: `rgba(30,30,32,0.52)` + 22 px blur; light: white 70 %);
  app icon 38 × 38 rounded-square (radius 9.5) green `#5DF277 → #30D158 → #28B04A` with a white speech bubble (our
  own drawing) at x 14, vertically centered; title = sender (15, 600) at x 64, right-aligned "now" / "2m ago" (13,
  400, white 60 %); body up to 4 lines (15/20) below the title.
- Flashlight and camera glass circles Ø 50 at the bottom corners (centers x 46 / 356, y 800).

### Screenshot moment (for the "Upload" step)
White flash (100 % → 0 % over ~6 frames), then the screen shrinks into a thumbnail at the bottom-left
(≈ 30 % size, radius 14, 2 pt white border, soft shadow) that holds, then flies off.

---------------------------------------------------------------------------------------------------
## 3. The conversations (exact copy)

**A. Strong (STOP ignored 17 days later)** — sender `+1 (833) 555-0142`, viewed on Thu Sep 18:
1. header "Text Message • SMS" / "Mon, Sep 1 at 3:01 PM"
2. received: "Domira Auto: We found a full auto policy at $59.75/mo for you. See what's covered: dom-ins.co/v6h3 Reply STOP to opt out"
3. sent: "STOP"
4. received: "You have been unsubscribed and will receive no further messages."
5. header "Today 9:12 AM"
6. received: "Domira Auto: Rates just dropped again! Lock in $49.99/mo before Friday: dom-ins.co/q2k Reply STOP to opt out"

**B. May qualify (STOP, timing unclear)** — sender `+1 (786) 555-0199`:
"You're pre-approved for up to $15,000. Reply YES to claim." / "Last chance: your $15,000 offer expires tonight." /
sent "STOP" / "Good news, your application was moved to the front of the line!" (no visible dates beyond "Yesterday").

**C. Weaker (one text, after a sign-up, no STOP)** — sender short code `88763`:
header "Today 11:40 AM" / "Thanks for requesting a solar quote! A specialist will reach out shortly. Reply STOP to opt out."

**Lock-screen notifications** (newest last): `+1 (833) 555-0142` "We found a full auto policy at $59.75/mo for you…";
`+1 (786) 555-0199` "You're pre-approved for up to $15,000. Reply YES to claim."; `88763` "FINAL NOTICE: Your vehicle
warranty expires today. Call now to keep coverage."; `+1 (305) 555-0123` "Hi! It's Amanda with HomeFast. Still thinking
about selling? Cash offer today."; `+1 (844) 555-0187` "Congrats! You've been selected for a $1,000 gift card. Claim: gft-rwd.co/x9".

**As rendered in the textures** (`ios-ui-kit/build-textures.mjs` holds this copy): A's links render as plain text
(unknown sender). B's only date line is "Yesterday 6:12 PM" (header "Text Message • SMS" / "Yesterday 6:12 PM"; no
timestamp between the STOP and the next text). C's header is "Text Message • SMS" / "Today 11:40 AM". Lock-screen
ages run newest-first "now", "2m ago", "5m ago", "9m ago", "14m ago" (lock_k shows the first k notifications).

**Verification copy (the reference screenshot, not for the pages)**: sender `+1 (833) 336-2704`, status 5:04, silent;
"Text Message • SMS" / "Tuesday 3:01 PM"; received "Domilina: We found a full auto policy at 59.75 for you, See what is
covered: https://domilina.com/v6he9y Reply STOP to opt out"; "Today 5:04 AM"; sent "Stop"; received "NETWORK MSG: You
replied with the word "stop" which blocks all texts sent from this number. Text back "unstop" or "start" to receive
messages again."
