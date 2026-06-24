# TypeRush

A gamified speed-typing trainer — one self-contained HTML file, zero dependencies.

## How to play

1. Double-click `index.html` (or drag it into any browser).
2. Pick a duration (15 / 30 / 60 s) and difficulty (Easy / Medium / Hard).
3. Click **PLAY** — start typing the words shown. The clock starts on your first keystroke.
4. When time runs out, see your WPM, accuracy, and a WPM-over-time chart.

## Controls

| Key | Action |
|-----|--------|
| `Tab` | Restart immediately (game or results screen) |
| `Enter` | Restart from results screen |
| `Esc` | Back to menu |
| `Space` | Submit current word |

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
- Personal bests saved per duration+difficulty combination.
- Achievements (First 40 WPM, 100% accuracy, 50× combo, etc.).
- Dark / light theme toggle.
- Optional keypress sounds (WebAudio, fully client-side).
- Fully offline — no network requests.
