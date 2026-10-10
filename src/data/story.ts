// The scroll story's copy, timed to the Blender sequence (t = scroll progress through the story, 0..1).
// Keep these numbers in sync with the beats in blender/story.py (ACTS, STOP_T, SHOT_T, the act-4 close-ups).
// Copy rules: "may" / "could" wording, no dollar amounts, no promises, no attorney names.

export type Beat = {
  id: string;
  in: number; // fully visible from here (fades in over FADE before it)
  out: number; // fully gone by here (fades out over FADE before it)
  eyebrow?: string;
  title: string;
  body?: string;
  checks?: { ok: boolean; text: string }[];
  tone?: 'strong' | 'maybe' | 'weak';
  cta?: boolean;
  heading?: 'h1' | 'h2' | 'h3';
};

export const FADE = 0.022;

export const ACTS = [
  { id: 'hero', t: 0.0, label: 'Start' },
  { id: 'stop', t: 0.19, label: 'STOP' },
  { id: 'again', t: 0.385, label: 'Again' },
  { id: 'examples', t: 0.53, label: 'Examples' },
  { id: 'how', t: 0.75, label: 'How it works' },
  { id: 'finale', t: 0.9, label: 'Check' },
] as const;

export const BEATS: Beat[] = [
  {
    id: 'hero',
    in: -1,
    out: 0.15,
    eyebrow: 'Spam texts after STOP',
    title: 'You said STOP.<br/>They kept texting.',
    body: 'See if your screenshots may qualify for attorney review.',
    cta: true,
    heading: 'h1',
  },
  {
    id: 'stop',
    in: 0.205,
    out: 0.35,
    eyebrow: 'Day one',
    title: 'You replied STOP.',
    body: 'They even texted back to say you were unsubscribed and would get no further messages.',
  },
  {
    id: 'again',
    in: 0.4,
    out: 0.505,
    eyebrow: '17 days later',
    title: 'They texted again.',
    body: 'Marketing texts after you opt out may violate the Telephone Consumer Protection Act (TCPA).',
  },
  {
    id: 'examples',
    in: 0.548,
    out: 0.59,
    eyebrow: 'Pattern check',
    title: 'Do your texts look like this?',
  },
  {
    id: 'strong',
    in: 0.6,
    out: 0.632,
    tone: 'strong',
    eyebrow: 'Strong pattern',
    title: 'STOP, then more marketing',
    heading: 'h3',
    checks: [
      { ok: true, text: 'STOP is visible' },
      { ok: true, text: 'Texts kept coming after it' },
      { ok: true, text: 'Dates are visible' },
    ],
  },
  {
    id: 'maybe',
    in: 0.645,
    out: 0.677,
    tone: 'maybe',
    eyebrow: 'May qualify',
    title: 'STOP, but the dates are unclear',
    heading: 'h3',
    checks: [
      { ok: true, text: 'STOP is visible' },
      { ok: true, text: 'Texts kept coming after it' },
      { ok: false, text: 'Dates are hard to see' },
    ],
  },
  {
    id: 'weak',
    in: 0.69,
    out: 0.722,
    tone: 'weak',
    eyebrow: 'Weaker',
    title: 'One text after you signed up',
    heading: 'h3',
    checks: [
      { ok: false, text: 'No STOP reply' },
      { ok: false, text: 'Only one text' },
      { ok: true, text: 'The date is visible' },
    ],
  },
  {
    id: 'how',
    in: 0.765,
    out: 0.875,
    eyebrow: 'How it works',
    title: 'Screenshot the thread.<br/>We read every detail.',
    body: 'We find your STOP, check the dates and flag every text that came after it. A participating attorney then reviews what may qualify.',
  },
  {
    id: 'finale',
    in: 0.915,
    out: 2,
    eyebrow: 'Free to check',
    title: 'See if your texts<br/>may qualify.',
    body: 'Upload your screenshots. No sign-up, no cost to check.',
    cta: true,
  },
];

// reduced motion: one representative frame per beat instead of a continuous scrub
export const STILLS = [0.0, 0.11, 0.3, 0.46, 0.565, 0.61, 0.655, 0.7, 0.83, 1.0];
