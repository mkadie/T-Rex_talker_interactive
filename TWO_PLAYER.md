# T-Rex's Rubber Chicken Challenge — Two-Player Mode

A real-time head-to-head race built on the AAC Trainer
(`stim_games/aac_trainer.py`). Two players share one screen and one prompt
and race to buzz in the correct answer.

## Controls

Each player drives their own cursor with their own three inputs (a
sip-n-puff or keyboard emulating these keys):

| Player | Move back (−1) | Move forward (+1) | Select |
|--------|----------------|-------------------|--------|
| **Player 1** | Left  | Right | **Space** |
| **Player 2** | Up    | Down  | **Enter** |

- **Player 1** has the **yellow** cursor; it resets to **cell 1** each question.
- **Player 2** has the **blue** cursor; it resets to **cell 8** each question.
- Both cursors move at the same time. Cursors wrap around the 8-cell grid.

Multiple sip-n-puff / keyboard devices are polled at once, so the two
players' adapters are both live simultaneously.

## Gameplay

1. Both players hear the same spoken prompt. Input is ignored while it plays.
2. When the prompt finishes, both race — moving their cursors in real time.
3. **The first selection ends the question** — whoever buzzes in first (P1
   Space or P2 Enter) locks the answer. The other player does not get to
   answer that question.
4. The selected word + a correct / try-again cue play, then the next
   question loads. A game is `rounds` questions (default 6); questions do
   not repeat within a game.

## Scoring (lower time wins)

Time is the score. Each question's **elapsed race time is added to BOTH
players** (the clock is shared). Then a 30-second penalty is applied:

- **Correct** selection → the **other** player has **+30 s** added to their
  time (they were too slow / didn't answer).
- **Incorrect** selection → the player who **buzzed in** has **+30 s** added
  to their **own** time.

At the end of the game **both players are eligible for the high-score
table**, entered one after the other.

## The "sacrifice" cheat (intentional / accepted)

Because ending a question fast minimizes the shared elapsed time, two
cooperating players can game the leaderboard: **Player A buzzes in as fast
as possible (even wrong)** to end each question instantly. Player A eats the
+30 s penalties, but **Player B accrues almost no elapsed time**, ending with
a near-perfect minimum score. **This is a known, accepted behavior** — it's
fun at a booth and harmless. No mitigation is applied.

## Design notes / limitations

- **Base-page questions only.** Two-player uses the 7 single-step base
  answers (tired, happy, bathroom, stinky, yes, no, please). The multi-step
  **food** questions (answered via the **More** button) are **excluded**,
  because the board is shared: if one player opened the food page it would
  yank the board out from under the other. `More` is still on the board — a
  player who selects it simply gets a wrong answer.
- **Name entry** starts each slot on `-` so you can see which letter you're
  dialing in (rotate with your move keys, advance with your select key).
- The live **score bar** along the bottom shows both players' running times
  (P1 yellow left, P2 blue right). The round timer pauses during all audio.

## Configuration

In `stim_games/aac_trainer.cfg` (header):

```
# two_player = true    # default; set false for the classic single-player game
rounds = 6
penalty_seconds = 30
```

Single-player mode (`two_player = false`) keeps the original one-cursor,
food-navigation game with time + 30 s penalties.

## Hardware note

The Fruit Jam USB host enumerates devices only at power-on / hard reset
(`boot.py`), so **both sip-n-puffs must be plugged in before the board is
powered on / reset**. If the host gets into a bad state (repeated
`USBError` / `keyboards=0`), fully power-cycle the board. See
`documents/` and the project memory for the SD / USB hard-reset gotchas.
