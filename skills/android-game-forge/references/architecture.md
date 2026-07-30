# Engine architecture

The whole design exists to keep one rule true: **simulation is plain Kotlin, rendering is one Canvas, and Compose recomposes once per frame — not once per entity.**

A Compose game that stores entities in `mutableStateOf` and emits a composable per entity will stutter at 40 entities on a mid-range phone. The structure below holds 500.

## File layout

```
game/GameConfig.kt   // every tunable number, one place
game/Entities.kt     // mutable data holders, pooled
game/GameState.kt    // update(dt): List<GameEvent>   ← no Compose imports at all
game/Engine.kt       // the frame loop composable + Canvas draw
platform/SoundBank.kt
platform/Haptics.kt
platform/Prefs.kt
platform/Feedback.kt // fans one call out to sound + haptics together
```

`GameState.kt` must not import anything from `androidx.compose`. If it does, simulation and rendering are entangled and neither is testable.

## Virtual coordinates

All physics runs in a fixed **1000 × 1778** virtual space (portrait 9:16), scaled uniformly onto the canvas at draw time:

```kotlin
val scale = min(size.width / VW, size.height / VH)
val ox = (size.width  - VW * scale) / 2f
val oy = (size.height - VH * scale) / 2f
fun Offset.toScreen() = Offset(ox + x * scale, oy + y * scale)
```

Tuning gravity against a device's pixel height means the game plays differently on every phone. Tune it once against 1778.

## Frame loop

```kotlin
var frame by remember { mutableIntStateOf(0) }
LaunchedEffect(running) {
    var last = 0L
    while (running) {
        withFrameNanos { now ->
            if (last != 0L) {
                val dt = ((now - last) / 1_000_000_000f).coerceAtMost(1f / 30f)
                state.update(dt).forEach(::handleEvent)   // events → feedback, not state
            }
            last = now
            frame++
        }
    }
}
Canvas(Modifier.fillMaxSize()) { frame; state.draw(this) }
```

- **`dt` is clamped to `1f / 30f`.** Without it, a GC pause or a resume from background delivers a 400ms `dt`, every entity teleports through its collider, and the player dies for no visible reason. This is the single most common "the game is broken" bug in hand-written Compose games.
- `frame` is read inside the Canvas lambda to establish the read dependency. One state read, one recomposition, everything redrawn.
- No allocation inside `update` or `draw`: no `map`, `filter`, `listOf`, or lambda capture in the hot path. Iterate with indexed `for` loops over pre-sized `ArrayList`s and reuse pooled entities behind an `active` flag.

## Events, not callbacks

`update` returns `List<GameEvent>` — `Scored(points)`, `Hit`, `Milestone(n)`, `GameOver(score)`, `Won`. The loop maps events to `Feedback` and UI state.

This is why the engine has no dependency on sound, haptics, or navigation. It also makes the juice rules trivially satisfiable: `Hit` → shake + `hit()`, `Milestone` → particle burst, `Scored` → counter pop.

## Feedback

```kotlin
class Feedback(ctx: Context, val prefs: Prefs) {
    fun tap()      // rate-limited to 40ms
    fun score(); fun hit(); fun gameOver(); fun win()
}
```

Every call fires **SoundPool and Vibrator together**, each gated by its own pref (`soundOn`, `hapticsOn`). One method per game moment, never `playSound()` at call sites — otherwise haptics drift out of sync with audio as screens get edited.

Rate-limiting `tap()` to 40ms matters: an unthrottled rapid-tap queues dozens of vibration requests and the phone buzzes for a second after the player stops.

`SoundPool` needs real files in `res/raw/`. If there are none, **stub every method to a no-op and say so in the report** — a `R.raw.tap` that does not exist is a compile error, not a missing sound.

## Persistence

`SharedPreferences` only, wrapped in `Prefs`: `highscore`, `level`, `soundOn`, `hapticsOn`, `reduceMotion`, `gamesPlayed`. Load once at startup. No Room, no DataStore, no coroutine ceremony for six values.

`reduceMotion` is not decoration. It is read by `AnimatedGameBackground`, `rememberShake`, `ParticleSystem`, and the screen-transition animation, and it is exposed in Settings next to sound and haptics. See the accessibility section of `design-system.md` for exactly what each one does when it is on.

## The ambient background during play

`AnimatedGameBackground` runs an infinite transition. That is correct on the six menu screens and wrong during a live run: it is a second continuously-recomposing source competing with the frame loop for the same 16ms.

While `running` is true, freeze it — hold the last blob positions and stop the transition. The gradient stays on screen, so the palette never breaks, but the only thing animating during gameplay is the one `Canvas` that matters. Resume it when the run ends or Pause opens.

## Navigation

```kotlin
sealed interface Screen { object Splash; object Home; /* … */ }
var screen by remember { mutableStateOf<Screen>(Screen.Splash) }
```

No navigation-compose, no Hilt. **Pause and Result are overlays drawn above the live canvas**, not destinations — routing them as screens tears down the game state and forces a save/restore layer that buys nothing.

`BackHandler` during play opens Pause. It never exits the app; losing a run to a stray back-swipe is the fastest way to a one-star review.

`FLAG_KEEP_SCREEN_ON` while playing, cleared on pause. A game that dims mid-run during a hold input feels broken.

## Lifecycle

On `ON_PAUSE`: pause the loop, `SoundPool.autoPause()`, and open the Pause overlay. Resuming with a live loop but a stale `last` timestamp is exactly the giant-`dt` case the clamp protects against — clamp *and* reset `last = 0L`.

## Performance floor

Target 60fps on a mid-range device: entity updates under 4ms, draw under 8ms. If it drops, the cause is almost always allocation in the hot path or a `Brush` being rebuilt per frame — hoist brushes and paints outside the draw call with `remember`.
