# TypeRush

A gamified speed-typing trainer — one self-contained HTML file, zero dependencies.

## Two modes

**⌨️ Free Mode** — Monkeytype-style speed test. Race a stream of words against a
15 / 30 / 60 s clock. Pick a difficulty (Easy / Medium / Hard) and optional
modifiers (numbers, punctuation, strict). Pure speed.

**📖 Story Mode** — TypeRacer-style. Type a real passage of classic literature
that reads as complete, grammatical prose (Three Little Pigs, The Great Gatsby,
Jekyll & Hyde, Alice in Wonderland, Sherlock Holmes). There is no countdown — you
*race to the end* of the passage while the timer counts up, with a live progress
bar. Each replay serves the next excerpt of that story. Errors must be corrected
before you can continue, so what you type always matches the text.

## How to play

1. Double-click `index.html` (or drag it into any browser).
2. Pick **Free Mode** or **Story Mode** and configure it.
3. Click **PLAY** — start typing. The timer starts on your first keystroke.
4. When the run ends, see your WPM, accuracy, consistency, and a WPM-over-time chart.

## Controls

| Key | Action |
|-----|--------|
| `Tab` | Restart immediately (game or results screen) |
| `Enter` | Restart from results screen |
| `Esc` | Back to menu |
| `Space` | Submit current word (Free Mode) |
| `Backspace` | Fix a mistake (both modes) |

## Scoring

- Each correct character = 10 pts × your current combo multiplier.
- **Combo** grows with every correct word, resets on a mistake.
- Multiplier: ×1 base → ×1.5 at 5× → ×2 at 10× → ×3 at 25× → ×4 at 50×.
- **XP** is awarded at the end of each run (score/10 + WPM×2).
- Level up by filling the XP bar — progress is saved between sessions.

## Features

- Live WPM, accuracy, score, and combo during the game.
- Combo streak meter with milestone glow at 10/25/50/100×.
- WPM-over-time chart on the results screen.
- **Trouble keys**: shows which characters you mis-hit most.
- Personal bests saved per Free-Mode duration+difficulty and per story.
- Achievements (First 40 WPM, 100% accuracy, 50× combo, etc.).
- Dark / light theme toggle.
- Optional keypress sounds (WebAudio, fully client-side).
- Fully offline — no network requests.
