import { useEffect, useRef, useState } from "react";
import MobileControls from "../../components/ui/MobileControls";
import { useGameSession } from "../../services/progression/useGameSession";
import type { ControlScheme } from "../../types/settings";
import "../neon_blob_dash/runner.css";

const W = 540;
const H = 900;
const GROUND_Y = Math.floor(H * 0.82);

const MAX_FALL = 18;
const COYOTE_T = 8 / 60;
const JUMP_BUF_T = 8 / 60;
const INVULN_T = 1.2;
const HIT_FLASH_T = 0.26;
const STOMP_INVULN = 0.22;
const BOSS_INVULN = 0.32;
const SAFE_LOCK_T = 0.9;
const DOUBLE_T = 9;
const JUMPBOOST_T = 8;
const STAR_T = 7;
const SHOT_CD = 0.15;
const BOSS_CD = 0.22;

interface Difficulty {
  name: "Easy" | "Medium" | "Hard";
  baseSpeed: number;
  maxSpeed: number;
  gravity: number;
  jumpPower: number;
  gapMin: number;
  gapMax: number;
  enemyChance: number;
  spikeChance: number;
  bossHp: number;
  bossInterval: number;
}

const DIFFICULTIES: Difficulty[] = [
  {
    name: "Easy",
    baseSpeed: 4.6,
    maxSpeed: 7.1,
    gravity: 0.72,
    jumpPower: -16.4,
    gapMin: 55,
    gapMax: 115,
    enemyChance: 0.3,
    spikeChance: 0.28,
    bossHp: 3,
    bossInterval: 3800
  },
  {
    name: "Medium",
    baseSpeed: 5.2,
    maxSpeed: 8.1,
    gravity: 0.78,
    jumpPower: -15.5,
    gapMin: 70,
    gapMax: 145,
    enemyChance: 0.45,
    spikeChance: 0.38,
    bossHp: 4,
    bossInterval: 3350
  },
  {
    name: "Hard",
    baseSpeed: 5.9,
    maxSpeed: 9.2,
    gravity: 0.84,
    jumpPower: -14.6,
    gapMin: 85,
    gapMax: 170,
    enemyChance: 0.58,
    spikeChance: 0.48,
    bossHp: 5,
    bossInterval: 2900
  }
];

type Phase = "select" | "game";
type PowerType = "shield" | "double" | "jump" | "blaster" | "star";

interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}

interface Coin {
  x: number;
  y: number;
  alive: boolean;
}

interface Powerup {
  x: number;
  y: number;
  type: PowerType;
  alive: boolean;
}

interface Enemy {
  rect: Rect;
  minX: number;
  maxX: number;
  dir: -1 | 1;
  speed: number;
}

interface Shot {
  x: number;
  y: number;
  vx: number;
  alive: boolean;
}

interface Boss {
  rect: Rect;
  hp: number;
  maxHp: number;
  dir: -1 | 1;
  speed: number;
  stun: number;
  recover: number;
}

interface Runtime {
  phase: Phase;
  diffIndex: number;
  d: Difficulty;

  player: Rect;
  px: number;
  py: number;
  vx: number;
  vy: number;
  facing: -1 | 1;
  onGround: boolean;

  speed: number;
  score: number;
  lives: number;
  dist: number;
  coins: number;
  best: number;
  newBest: boolean;

  gameOver: boolean;
  paused: boolean;
  sessionSaved: boolean;

  coyoteT: number;
  jumpBufT: number;
  invulnT: number;
  hitFlashT: number;
  stompGrace: number;
  bossCdT: number;
  safeLockT: number;
  doubleT: number;
  jumpBoostT: number;
  starT: number;
  starHitCd: number;
  shotCd: number;

  shields: number;
  blaster: boolean;
  stompChain: number;

  shots: Shot[];
  platforms: Rect[];
  spikes: Rect[];
  coinList: Coin[];
  powerups: Powerup[];
  enemies: Enemy[];
  boss: Boss | null;

  groundScroll: number;
  scrollCarry: number;
  nextSpawnX: number;
  lastSpawnY: number;
  bossNextDist: number;
  consecElevated: number;

  safeX: number;
  safeY: number;
  safeDist: number;

  coinCd: number;
  powerupCd: number;
}

interface HudState {
  score: number;
  best: number;
  lives: number;
  diff: string;
  paused: boolean;
  gameOver: boolean;
  newBest: boolean;
  powerText: string;
  shields: number;
  distance: number;
}

interface EndlessMetroRunGameProps {
  onExit: () => void;
  controlScheme: ControlScheme;
}

function EndlessMetroRunGame({ onExit, controlScheme }: EndlessMetroRunGameProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const frameRef = useRef<number | null>(null);
  const lastRef = useRef<number | null>(null);

  const phaseRef = useRef<Phase>("select");
  const selRef = useRef(1);
  const keysRef = useRef<Set<string>>(new Set());

  const [phase, setPhase] = useState<Phase>("select");
  const [sel, setSel] = useState(1);
  const [bestScore, setBestScore] = useState(() => readBestScore());
  const [hud, setHud] = useState<HudState>({
    score: 0,
    best: bestScore,
    lives: 3,
    diff: "Medium",
    paused: false,
    gameOver: false,
    newBest: false,
    powerText: "No Powerups",
    shields: 0,
    distance: 0
  });

  const runtimeRef = useRef<Runtime>(createRunRuntime(1, bestScore));
  const session = useGameSession("endless_metro_run");

  const syncHud = (rt: Runtime) => {
    setHud({
      score: rt.score,
      best: Math.max(rt.best, rt.score),
      lives: rt.lives,
      diff: rt.d.name,
      paused: rt.paused,
      gameOver: rt.gameOver,
      newBest: rt.newBest,
      powerText: powerStatus(rt),
      shields: rt.shields,
      distance: Math.floor(rt.dist)
    });
  };

  const finishRun = (rt: Runtime) => {
    if (rt.sessionSaved) {
      return;
    }
    rt.sessionSaved = true;
    session.recordResult({
      score: rt.score,
      won: false,
      extra: {
        difficulty: rt.d.name.toLowerCase(),
        distance: Math.floor(rt.dist),
        coins: rt.coins
      }
    });

    if (rt.score > bestScore) {
      setBestScore(rt.score);
      writeBestScore(rt.score);
    }
  };

  const startRun = (diffIndex: number) => {
    const idx = clamp(diffIndex, 0, DIFFICULTIES.length - 1);
    selRef.current = idx;
    setSel(idx);
    phaseRef.current = "game";
    setPhase("game");

    session.restartSession();
    runtimeRef.current = createRunRuntime(idx, bestScore);
    syncHud(runtimeRef.current);
  };

  const goToSelect = () => {
    const rt = runtimeRef.current;
    if (phaseRef.current === "game") {
      finishRun(rt);
    }

    phaseRef.current = "select";
    setPhase("select");
    runtimeRef.current = createRunRuntime(selRef.current, bestScore);
    syncHud(runtimeRef.current);
  };

  const exitToMenu = () => {
    if (phaseRef.current === "game") {
      finishRun(runtimeRef.current);
    } else {
      session.recordPlaytimeOnly();
    }
    onExit();
  };

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      keysRef.current.add(event.key);

      if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", " ", "Spacebar"].includes(event.key)) {
        event.preventDefault();
      }

      if (event.key === "q" || event.key === "Escape") {
        if (phaseRef.current === "game") {
          exitToMenu();
          return;
        }
        exitToMenu();
        return;
      }

      if (phaseRef.current === "select") {
        if (event.key === "ArrowUp") {
          const next = (selRef.current + DIFFICULTIES.length - 1) % DIFFICULTIES.length;
          selRef.current = next;
          setSel(next);
          return;
        }
        if (event.key === "ArrowDown") {
          const next = (selRef.current + 1) % DIFFICULTIES.length;
          selRef.current = next;
          setSel(next);
          return;
        }
        if (event.key === "Enter" || event.key === " " || event.key === "Spacebar") {
          startRun(selRef.current);
        }
        return;
      }

      const rt = runtimeRef.current;

      if ((event.key === "p" || event.key === "P") && !rt.gameOver) {
        rt.paused = !rt.paused;
        syncHud(rt);
        return;
      }

      if (event.key === "r") {
        startRun(rt.diffIndex);
        return;
      }

      if (event.key === "n") {
        goToSelect();
        return;
      }

      if (event.key === " " || event.key === "Spacebar" || event.key === "ArrowUp" || event.key === "w" || event.key === "W") {
        rt.jumpBufT = JUMP_BUF_T;
      }

      if (["f", "F", "Control", "Meta"].includes(event.key)) {
        fireShot(rt);
      }
    };

    const onKeyUp = (event: KeyboardEvent) => {
      keysRef.current.delete(event.key);
    };

    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
    };
  }, [bestScore]);

  useEffect(() => {
    const tick = (time: number) => {
      if (lastRef.current == null) {
        lastRef.current = time;
      }
      const dt = Math.min(0.05, (time - lastRef.current) / 1000);
      lastRef.current = time;

      const rt = runtimeRef.current;

      if (phaseRef.current === "game") {
        updateGame(rt, dt, keysRef.current, finishRun);
        if (rt.score > rt.best) {
          rt.best = rt.score;
          rt.newBest = true;
        }
        if (rt.best > bestScore) {
          setBestScore(rt.best);
          writeBestScore(rt.best);
        }
        syncHud(rt);
      }

      drawMetro(canvasRef.current, rt, selRef.current, phaseRef.current === "select");

      frameRef.current = window.requestAnimationFrame(tick);
    };

    frameRef.current = window.requestAnimationFrame(tick);
    return () => {
      if (frameRef.current != null) {
        window.cancelAnimationFrame(frameRef.current);
      }
    };
  }, [bestScore]);

  return (
    <section className="runner-screen">
      <header className="runner-header">
        <div>
          <h1>Endless Metro Run</h1>
          <p>Select difficulty, then run, jump, collect, and survive. P pause, R restart, N select.</p>
        </div>
        <button type="button" onClick={exitToMenu}>Back to Menu</button>
      </header>

      <canvas ref={canvasRef} className="runner-canvas" width={W} height={H} />

      <div className="runner-hud-line">
        {phase === "game" ? (
          <>
            <span>Score: {hud.score}</span>
            <span>Best: {Math.max(hud.best, bestScore)}</span>
            <span>Lives: {hud.lives}</span>
            <span>Shields: {hud.shields}</span>
            <span>Dist: {hud.distance}</span>
            <span>{hud.diff}</span>
            {hud.paused && <span>Paused</span>}
            {hud.gameOver && <span>Game Over</span>}
          </>
        ) : (
          <>
            <span>Select difficulty and start.</span>
            <span>Current: {DIFFICULTIES[sel].name}</span>
          </>
        )}
      </div>

      {controlScheme === "buttons" && phase === "select" && (
        <MobileControls
          dpad={{
            up: () => {
              const next = (selRef.current + DIFFICULTIES.length - 1) % DIFFICULTIES.length;
              selRef.current = next;
              setSel(next);
            },
            down: () => {
              const next = (selRef.current + 1) % DIFFICULTIES.length;
              selRef.current = next;
              setSel(next);
            }
          }}
          actions={[
            { label: "Start", onPress: () => startRun(selRef.current) },
            { label: "Menu", onPress: exitToMenu }
          ]}
        />
      )}

      {controlScheme === "buttons" && phase === "game" && (
        <MobileControls
          dpad={{
            left: () => movePlayerHorizontal(runtimeRef.current, -22),
            right: () => movePlayerHorizontal(runtimeRef.current, 22)
          }}
          actions={[
            {
              label: "Jump",
              onPress: () => {
                runtimeRef.current.jumpBufT = JUMP_BUF_T;
              }
            },
            {
              label: "Shoot",
              onPress: () => fireShot(runtimeRef.current)
            },
            {
              label: runtimeRef.current.paused ? "Resume" : "Pause",
              onPress: () => {
                const rt = runtimeRef.current;
                if (rt.gameOver) {
                  return;
                }
                rt.paused = !rt.paused;
                syncHud(rt);
              }
            },
            { label: "Restart", onPress: () => startRun(runtimeRef.current.diffIndex) },
            { label: "Select", onPress: goToSelect },
            { label: "Menu", onPress: exitToMenu }
          ]}
        />
      )}
    </section>
  );
}

function createRunRuntime(diffIndex: number, best: number): Runtime {
  const d = DIFFICULTIES[diffIndex] ?? DIFFICULTIES[1];

  return {
    phase: "game",
    diffIndex,
    d,

    player: { x: 190, y: GROUND_Y - 56, w: 42, h: 56 },
    px: 190,
    py: GROUND_Y - 56,
    vx: 0,
    vy: 0,
    facing: 1,
    onGround: false,

    speed: d.baseSpeed,
    score: 0,
    lives: 3,
    dist: 0,
    coins: 0,
    best,
    newBest: false,

    gameOver: false,
    paused: false,
    sessionSaved: false,

    coyoteT: 0,
    jumpBufT: 0,
    invulnT: 0,
    hitFlashT: 0,
    stompGrace: 0,
    bossCdT: 0,
    safeLockT: SAFE_LOCK_T,
    doubleT: 0,
    jumpBoostT: 0,
    starT: 0,
    starHitCd: 0,
    shotCd: 0,

    shields: 0,
    blaster: false,
    stompChain: 0,

    shots: [],
    platforms: [
      { x: 0, y: GROUND_Y, w: 500, h: H - GROUND_Y },
      { x: 560, y: GROUND_Y, w: 340, h: H - GROUND_Y }
    ],
    spikes: [],
    coinList: [{ x: 650, y: GROUND_Y - 86, alive: true }],
    powerups: [],
    enemies: [],
    boss: null,

    groundScroll: 0,
    scrollCarry: 0,
    nextSpawnX: 900,
    lastSpawnY: GROUND_Y,
    bossNextDist: d.bossInterval,
    consecElevated: 0,

    safeX: 190,
    safeY: GROUND_Y - 56,
    safeDist: 0,

    coinCd: 0.9,
    powerupCd: 6.2
  };
}

function updateGame(
  rt: Runtime,
  dt: number,
  keys: Set<string>,
  finishRun: (rt: Runtime) => void
): void {
  if (rt.phase !== "game") {
    return;
  }

  tickTimers(rt, dt);

  if (rt.paused || rt.gameOver) {
    return;
  }

  const dts = dt * 60;

  rt.speed = Math.min(rt.d.maxSpeed, rt.speed + 0.00009 * dts);

  const left = keys.has("ArrowLeft") || keys.has("a") || keys.has("A");
  const right = keys.has("ArrowRight") || keys.has("d") || keys.has("D");
  const move = left && !right ? -1 : right && !left ? 1 : 0;
  if (move !== 0) {
    rt.facing = move > 0 ? 1 : -1;
  }

  const running = keys.has("Shift") || keys.has("ShiftLeft") || keys.has("ShiftRight");
  const runMult = running ? 1.28 : 1;

  if (rt.onGround) {
    const target = move * 6.2 * runMult;
    rt.vx += (target - rt.vx) * 0.32;
  } else {
    const target = move * 7.0 * runMult;
    rt.vx += (target - rt.vx) * 0.28;
  }

  rt.px += rt.vx * dts;
  rt.px = clamp(rt.px, 70, W - 96);
  rt.player.x = Math.floor(rt.px);

  const bossActive = rt.boss != null;

  if (!bossActive) {
    let scroll = 0;
    const rAnchor = running ? 445 : 430;
    const lAnchor = 205;

    if (move > 0 && rt.px > rAnchor) {
      scroll = rt.px - rAnchor;
      rt.px = rAnchor;
    } else if (move < 0 && rt.px < lAnchor) {
      const back = Math.min(lAnchor - rt.px, rt.dist);
      scroll = -back;
      rt.px = lAnchor;
    }

    rt.player.x = Math.floor(rt.px);

    if (scroll !== 0) {
      rt.scrollCarry += scroll;
      const si = rt.scrollCarry >= 0 ? Math.floor(rt.scrollCarry) : Math.ceil(rt.scrollCarry);
      rt.scrollCarry -= si;
      if (si !== 0) {
        const applied = si;
        for (const p of rt.platforms) p.x -= applied;
        for (const s of rt.spikes) s.x -= applied;
        for (const c of rt.coinList) c.x -= applied;
        for (const pu of rt.powerups) pu.x -= applied;
        for (const e of rt.enemies) {
          e.rect.x -= applied;
          e.minX -= applied;
          e.maxX -= applied;
        }
        for (const shot of rt.shots) shot.x -= applied;

        rt.nextSpawnX -= applied;

        if (applied > 0) {
          rt.dist += applied;
        } else {
          rt.dist = Math.max(0, rt.dist + applied);
        }
        rt.groundScroll = (rt.groundScroll + applied) % 60;
      }
    }

    for (const enemy of rt.enemies) {
      enemy.rect.x += enemy.dir * enemy.speed;
      if (enemy.rect.x <= enemy.minX || enemy.rect.x >= enemy.maxX) {
        enemy.dir *= -1;
      }
    }

    rt.platforms = rt.platforms.filter((p) => p.x + p.w > -140);
    rt.spikes = rt.spikes.filter((s) => s.x + s.w > -90);
    rt.coinList = rt.coinList.filter((c) => c.x > -90 && c.alive);
    rt.powerups = rt.powerups.filter((p) => p.x > -90 && p.alive);
    rt.enemies = rt.enemies.filter((e) => e.rect.x + e.rect.w > -90);

    while (rt.nextSpawnX < W + 260) {
      spawnChunk(rt);
    }

    if (rt.dist >= rt.bossNextDist) {
      spawnBoss(rt);
      rt.bossNextDist += rt.d.bossInterval;
    }

    rt.coinCd -= dt;
    if (rt.coinCd <= 0 && rt.coinList.length < 4) {
      rt.coinCd = randomRange(1.3, 2.2);
      const minX = Math.floor(Math.max(rt.player.x + 150, 300));
      const maxX = W - 90;
      if (minX <= maxX) {
        const x = randomInt(minX, maxX);
        const y = GROUND_Y - pick([72, 86, 102]);
        const valid = rt.coinList.every((c) => Math.abs(c.x - x) > 130 || !c.alive);
        if (valid) {
          rt.coinList.push({ x, y, alive: true });
        }
      }
    }

    rt.powerupCd -= dt;
    if (rt.powerupCd <= 0 && rt.powerups.length < 1) {
      rt.powerupCd = randomRange(8.2, 12.0);
      const minX = Math.floor(Math.max(rt.player.x + 210, 360));
      const maxX = W - 120;
      if (minX <= maxX) {
        const x = randomInt(minX, maxX);
        const y = GROUND_Y - pick([114, 128]);
        const valid = rt.powerups.every((p) => Math.abs(p.x - x) > 220 || !p.alive);
        if (valid) {
          spawnPowerup(rt, x, y, true);
        }
      }
    }
  } else if (rt.boss) {
    if (rt.boss.stun > 0) {
      rt.boss.stun -= dt;
      rt.boss.recover = Math.max(rt.boss.recover, 0.26);
    } else if (rt.boss.recover > 0) {
      rt.boss.recover -= dt;
    } else {
      rt.boss.rect.x += rt.boss.dir * rt.boss.speed;
      if (rt.boss.rect.x <= 520) rt.boss.dir = 1;
      if (rt.boss.rect.x + rt.boss.rect.w >= W - 70) rt.boss.dir = -1;
    }
  }

  for (const shot of rt.shots) {
    if (!shot.alive) continue;

    shot.x += shot.vx * dts;
    const bulletRect = {
      x: shot.vx >= 0 ? shot.x : shot.x - 18,
      y: shot.y,
      w: 18,
      h: 4
    };

    if (rt.boss && rectOverlap(bulletRect, rt.boss.rect) && rt.boss.stun <= 0) {
      shot.alive = false;
      hitBoss(rt);
      continue;
    }

    for (const enemy of rt.enemies) {
      if (rectOverlap(bulletRect, enemy.rect)) {
        shot.alive = false;
        enemy.rect.x = -2000;
        addPoints(rt, 40);
        break;
      }
    }
  }

  rt.shots = rt.shots.filter((shot) => shot.alive && shot.x > -120 && shot.x < W + 120);

  if (rt.onGround) {
    rt.coyoteT = COYOTE_T;
  }

  if (rt.jumpBufT > 0 && rt.coyoteT > 0) {
    rt.vy = rt.d.jumpPower - (rt.jumpBoostT > 0 ? 1.8 : 0);
    rt.onGround = false;
    rt.coyoteT = 0;
    rt.jumpBufT = 0;
  }

  const jumpHeld = keys.has(" ") || keys.has("Spacebar") || keys.has("ArrowUp") || keys.has("w") || keys.has("W");
  if (rt.vy < 0 && !jumpHeld) {
    rt.vy += 0.62 * dts;
  }

  rt.vy += rt.d.gravity * dts;
  rt.vy = Math.min(rt.vy, MAX_FALL);

  const prevBottom = rt.player.y + rt.player.h;
  const prevVy = rt.vy;

  rt.py += rt.vy * dts;
  rt.player.y = Math.floor(rt.py);
  rt.onGround = false;

  for (const platform of rt.platforms) {
    if (!rectOverlap(rt.player, platform)) continue;

    if (rt.vy >= 0 && prevBottom <= platform.y + 8) {
      rt.player.y = platform.y - rt.player.h;
      rt.py = rt.player.y;
      rt.vy = 0;
      rt.onGround = true;
    } else if (rt.vy < 0) {
      rt.player.y = platform.y + platform.h;
      rt.py = rt.player.y;
      rt.vy = 0;
    }
  }

  if (rt.boss && rt.player.y + rt.player.h >= GROUND_Y) {
    rt.player.y = GROUND_Y - rt.player.h;
    rt.py = rt.player.y;
    rt.vy = 0;
    rt.onGround = true;
  }

  if (rt.onGround) {
    rt.stompChain = 0;
  }

  if (rt.player.y > H + 90) {
    damage(rt, "hazard", finishRun);
  }

  if (!rt.boss) {
    for (const spike of rt.spikes) {
      if (rectOverlap(rt.player, spike)) {
        damage(rt, "hazard", finishRun);
        break;
      }
    }
  }

  if (!rt.boss) {
    for (const enemy of rt.enemies) {
      if (!rectOverlap(rt.player, enemy.rect)) continue;

      if (rt.starT > 0) {
        enemy.rect.x = -2000;
        addPoints(rt, 70);
        continue;
      }

      const overlapW = Math.min(rt.player.x + rt.player.w, enemy.rect.x + enemy.rect.w) - Math.max(rt.player.x, enemy.rect.x);
      const stomp = prevVy > 0 && prevBottom <= enemy.rect.y + 24 && rt.player.y + rt.player.h >= enemy.rect.y && overlapW >= 8;

      if (stomp) {
        rt.stompChain += 1;
        const bonus = 40 + Math.min(4, rt.stompChain - 1) * 20;
        rt.player.y = enemy.rect.y - rt.player.h - 1;
        rt.py = rt.player.y;
        rt.vy = -9;
        rt.stompGrace = Math.max(rt.stompGrace, STOMP_INVULN);
        enemy.rect.x = -2000;
        addPoints(rt, bonus);
      } else {
        rt.stompChain = 0;
        damage(rt, "enemy", finishRun);
        break;
      }
    }
  }

  if (rt.boss) {
    const bossRect = rt.boss.rect;
    if (rectOverlap(rt.player, bossRect)) {
      if (rt.starT > 0 && rt.starHitCd <= 0 && rt.boss.stun <= 0) {
        hitBoss(rt);
        rt.starHitCd = 0.24;
        addPoints(rt, 120);
      } else {
        const stomp =
          prevVy > 0 &&
          prevBottom <= bossRect.y + 22 &&
          rt.player.y + rt.player.h >= bossRect.y &&
          rt.player.x + rt.player.w * 0.5 >= bossRect.x + 2 &&
          rt.player.x + rt.player.w * 0.5 <= bossRect.x + bossRect.w - 2;

        if (stomp && rt.boss.stun <= 0) {
          rt.player.y = bossRect.y - rt.player.h - 1;
          rt.py = rt.player.y;
          rt.vy = -10.3;
          rt.stompGrace = Math.max(rt.stompGrace, BOSS_INVULN);
          rt.bossCdT = BOSS_CD;
          rt.boss.stun = 0.52;
          rt.boss.recover = 0.32;
          rt.boss.dir *= -1;
          hitBoss(rt);
        } else if (rt.boss.stun <= 0 && rt.boss.recover <= 0 && rt.stompGrace <= 0 && rt.bossCdT <= 0) {
          const pushDir = rt.player.x + rt.player.w / 2 < bossRect.x + bossRect.w / 2 ? -1 : 1;
          if (pushDir < 0) rt.player.x = bossRect.x - rt.player.w - 1;
          else rt.player.x = bossRect.x + bossRect.w + 1;
          rt.px = rt.player.x;
          rt.vx *= -0.35;
          damage(rt, "enemy", finishRun);
          rt.bossCdT = BOSS_CD;
        }
      }
    }
  }

  if (rt.onGround) {
    let danger = rt.spikes.some((s) => rectOverlap(rt.player, inflateRect(s, 8, 8)));
    if (!danger && rt.boss) {
      danger = rectOverlap(rt.player, rt.boss.rect);
    }
    if (!danger) {
      danger = rt.enemies.some((e) => rectOverlap(rt.player, e.rect));
    }

    if (!danger && rt.safeLockT <= 0 && rt.invulnT <= 0 && Math.abs(rt.vy) < 0.01 && rt.dist >= rt.safeDist + 130) {
      rt.safeX = rt.player.x;
      rt.safeY = rt.player.y;
      rt.safeDist = rt.dist;
    }
  }

  for (const coin of rt.coinList) {
    if (!coin.alive) continue;
    if (rectOverlap(rt.player, { x: coin.x - 10, y: coin.y - 10, w: 20, h: 20 })) {
      coin.alive = false;
      rt.coins += 1;
      addPoints(rt, 10);
    }
  }

  for (const powerup of rt.powerups) {
    if (!powerup.alive) continue;
    if (rectOverlap(rt.player, { x: powerup.x - 11, y: powerup.y - 11, w: 22, h: 22 })) {
      powerup.alive = false;
      if (powerup.type === "shield") rt.shields += 1;
      if (powerup.type === "double") rt.doubleT = DOUBLE_T;
      if (powerup.type === "jump") rt.jumpBoostT = JUMPBOOST_T;
      if (powerup.type === "blaster") rt.blaster = true;
      if (powerup.type === "star") {
        rt.starT = STAR_T;
        rt.starHitCd = 0;
      }
    }
  }
}

function movePlayerHorizontal(rt: Runtime, amount: number): void {
  if (rt.phase !== "game" || rt.paused || rt.gameOver) {
    return;
  }
  rt.px = clamp(rt.px + amount, 70, W - 96);
  rt.player.x = Math.floor(rt.px);
}

function fireShot(rt: Runtime): void {
  if (!rt.blaster || rt.shotCd > 0 || rt.gameOver) {
    return;
  }

  const facing = rt.facing;
  const sx = facing >= 0 ? rt.player.x + rt.player.w - 2 : rt.player.x - 16;
  rt.shots.push({
    x: sx,
    y: rt.player.y + rt.player.h / 2 - 4,
    vx: (11.5 + rt.speed * 0.25) * facing,
    alive: true
  });
  rt.shotCd = SHOT_CD;
}

function damage(rt: Runtime, source: "enemy" | "hazard", finishRun: (rt: Runtime) => void): void {
  if (rt.invulnT > 0 || rt.stompGrace > 0 || rt.gameOver) {
    return;
  }
  if (rt.starT > 0) {
    return;
  }

  if (source === "enemy" && rt.blaster) {
    rt.blaster = false;
    rt.invulnT = INVULN_T;
    rt.hitFlashT = HIT_FLASH_T;
    rt.safeLockT = Math.max(rt.safeLockT, SAFE_LOCK_T);
    return;
  }

  if (rt.shields > 0) {
    rt.shields -= 1;
    rt.invulnT = 1;
    rt.hitFlashT = HIT_FLASH_T;
    rt.safeLockT = Math.max(rt.safeLockT, SAFE_LOCK_T);
    return;
  }

  rt.lives -= 1;
  rt.hitFlashT = HIT_FLASH_T;
  if (rt.lives <= 0) {
    rt.gameOver = true;
    finishRun(rt);
    return;
  }

  rt.invulnT = INVULN_T;
  rt.safeLockT = Math.max(rt.safeLockT, SAFE_LOCK_T);

  let sx = rt.safeX;
  let sy = rt.safeY;
  let bestScore = Number.POSITIVE_INFINITY;

  const desiredCx = sx + rt.player.w * 0.5;
  for (const platform of rt.platforms) {
    if (platform.w < rt.player.w + 24) continue;

    let cx = clamp(desiredCx - rt.player.w * 0.5, platform.x + 8, platform.x + platform.w - rt.player.w - 8);
    let candidate = { x: cx, y: platform.y - rt.player.h, w: rt.player.w, h: rt.player.h };

    if (rt.spikes.some((s) => rectOverlap(candidate, inflateRect(s, 8, 8)))) {
      let found = false;
      for (const dx of [-24, 24, -48, 48, -72, 72]) {
        const ex = clamp(cx + dx, platform.x + 8, platform.x + platform.w - rt.player.w - 8);
        const alt = { x: ex, y: platform.y - rt.player.h, w: rt.player.w, h: rt.player.h };
        if (!rt.spikes.some((s) => rectOverlap(alt, inflateRect(s, 8, 8)))) {
          cx = ex;
          candidate = alt;
          found = true;
          break;
        }
      }
      if (!found) continue;
    }

    const score = Math.abs(candidate.x + candidate.w / 2 - desiredCx) + Math.abs(platform.y - GROUND_Y) * 0.35;
    if (score < bestScore) {
      bestScore = score;
      sx = candidate.x;
      sy = candidate.y;
    }
  }

  rt.px = sx;
  rt.py = sy;
  rt.safeX = sx;
  rt.safeY = sy;
  rt.player.x = Math.floor(sx);
  rt.player.y = Math.floor(sy);
  rt.vx = 0;
  rt.vy = -2;

  rt.spikes = rt.spikes.filter((s) => s.x > 500);
  rt.enemies = rt.enemies.filter((e) => e.rect.x > 500);
}

function tickTimers(rt: Runtime, dt: number): void {
  rt.coyoteT = Math.max(0, rt.coyoteT - dt);
  rt.jumpBufT = Math.max(0, rt.jumpBufT - dt);
  rt.invulnT = Math.max(0, rt.invulnT - dt);
  rt.hitFlashT = Math.max(0, rt.hitFlashT - dt);
  rt.stompGrace = Math.max(0, rt.stompGrace - dt);
  rt.bossCdT = Math.max(0, rt.bossCdT - dt);
  rt.safeLockT = Math.max(0, rt.safeLockT - dt);
  rt.doubleT = Math.max(0, rt.doubleT - dt);
  rt.jumpBoostT = Math.max(0, rt.jumpBoostT - dt);
  rt.starT = Math.max(0, rt.starT - dt);
  rt.starHitCd = Math.max(0, rt.starHitCd - dt);
  rt.shotCd = Math.max(0, rt.shotCd - dt);
}

function addPoints(rt: Runtime, base: number): void {
  rt.score += Math.floor(base * (rt.doubleT > 0 ? 2 : 1));
}

function hitBoss(rt: Runtime): void {
  if (!rt.boss) {
    return;
  }

  rt.boss.hp -= 1;
  rt.boss.stun = 0.52;
  rt.boss.recover = 0.32;
  rt.boss.dir *= -1;

  if (rt.boss.hp <= 0) {
    addPoints(rt, 280);
    if (Math.random() < 0.75) {
      spawnPowerup(rt, rt.boss.rect.x + rt.boss.rect.w / 2, rt.boss.rect.y - 40, false);
    }
    rt.boss = null;
  }
}

function spawnPowerup(rt: Runtime, x: number, y: number, allowBlaster: boolean): void {
  const pool: PowerType[] = rt.blaster || !allowBlaster
    ? ["shield", "double", "jump", "star"]
    : ["shield", "double", "jump", "blaster", "star"];

  rt.powerups.push({ x, y, type: pick(pool), alive: true });
}

function spawnChunk(rt: Runtime): void {
  const forceGround = rt.consecElevated >= 2;
  const gap = randomInt(rt.d.gapMin, Math.min(rt.d.gapMax, 130));
  const x = rt.nextSpawnX + gap;

  const chooseGround = forceGround || Math.random() < 0.65;

  let y: number;
  let w: number;
  let h: number;

  if (chooseGround) {
    y = GROUND_Y;
    w = randomInt(240, 420);
    h = H - y;
    rt.consecElevated = 0;
  } else {
    const maxRise = Math.min(Math.floor((Math.abs(rt.d.jumpPower) ** 2) / (2 * rt.d.gravity)), 155);
    const prevY = rt.lastSpawnY;

    let minY: number;
    let maxY: number;

    if (prevY === GROUND_Y) {
      minY = GROUND_Y - maxRise;
      maxY = GROUND_Y - 55;
    } else {
      minY = Math.max(GROUND_Y - maxRise, prevY - 120);
      maxY = Math.min(GROUND_Y - 40, prevY + 80);
    }

    minY = Math.max(minY, GROUND_Y - 150);
    maxY = Math.max(maxY, minY + 10);

    y = randomInt(minY, maxY);
    w = randomInt(180, 300);
    h = 20;
    rt.consecElevated += 1;
  }

  const seg: Rect = { x, y, w, h };
  rt.platforms.push(seg);

  if (y === GROUND_Y && w > 240 && Math.random() < rt.d.spikeChance) {
    const sw = randomInt(28, 52);
    const sx = randomInt(seg.x + 50, seg.x + seg.w - sw - 50);
    if (sx + sw <= seg.x + seg.w - 20) {
      rt.spikes.push({ x: sx, y: GROUND_Y - 18, w: sw, h: 18 });
    }
  }

  if (y < GROUND_Y && w > 200 && Math.random() < rt.d.enemyChance) {
    const ex = randomInt(seg.x + 26, seg.x + seg.w - 56);
    rt.enemies.push({
      rect: { x: ex, y: y - 30, w: 30, h: 30 },
      minX: seg.x + 12,
      maxX: seg.x + seg.w - 42,
      dir: Math.random() < 0.5 ? -1 : 1,
      speed: randomRange(1.2, 2.0)
    });
  }

  rt.nextSpawnX = seg.x + seg.w;
  rt.lastSpawnY = y;
}

function spawnBoss(rt: Runtime): void {
  rt.spikes = [];
  rt.enemies = [];
  rt.powerups = [];

  rt.boss = {
    rect: { x: W - 190, y: GROUND_Y - 86, w: 86, h: 86 },
    hp: rt.d.bossHp,
    maxHp: rt.d.bossHp,
    dir: -1,
    speed: 2.6 + rt.diffIndex * 0.4,
    stun: 0,
    recover: 0
  };
}

function drawMetro(canvas: HTMLCanvasElement | null, rt: Runtime, sel: number, showSelect: boolean): void {
  if (!canvas) {
    return;
  }
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    return;
  }

  const bg = ctx.createLinearGradient(0, 0, 0, H);
  bg.addColorStop(0, "#061224");
  bg.addColorStop(1, "#030812");
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, W, H);

  if (showSelect) {
    drawSelect(ctx, sel);
    return;
  }

  for (let i = 0; i < 5; i += 1) {
    const y = 120 + i * 56;
    ctx.strokeStyle = `rgba(${24 + i * 6}, ${30 + i * 6}, ${44 + i * 8}, 0.55)`;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(W, y);
    ctx.stroke();
  }

  ctx.fillStyle = "#242b38";
  ctx.fillRect(0, GROUND_Y, W, H - GROUND_Y);
  ctx.strokeStyle = "#2f3f5c";
  ctx.lineWidth = 2;
  for (let x = -60; x <= W + 60; x += 60) {
    const gx = Math.floor(x - rt.groundScroll);
    ctx.beginPath();
    ctx.moveTo(gx, GROUND_Y + 15);
    ctx.lineTo(gx + 30, GROUND_Y + 15);
    ctx.stroke();
  }

  for (const p of rt.platforms) {
    ctx.fillStyle = "#121d31";
    roundRect(ctx, p.x, p.y, p.w, p.h, 6);
    ctx.fill();
    ctx.strokeStyle = "#2b436a";
    ctx.lineWidth = 1;
    roundRect(ctx, p.x, p.y, p.w, p.h, 6);
    ctx.stroke();
  }

  for (const s of rt.spikes) {
    ctx.fillStyle = "#ff5d73";
    for (let x = s.x; x < s.x + s.w; x += 10) {
      ctx.beginPath();
      ctx.moveTo(x, s.y + s.h);
      ctx.lineTo(x + 5, s.y);
      ctx.lineTo(x + 10, s.y + s.h);
      ctx.closePath();
      ctx.fill();
    }
  }

  for (const coin of rt.coinList) {
    if (!coin.alive) continue;
    ctx.fillStyle = "#ffd166";
    ctx.beginPath();
    ctx.arc(coin.x, coin.y, 8, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#edf2f4";
    ctx.beginPath();
    ctx.arc(coin.x - 2, coin.y - 2, 2, 0, Math.PI * 2);
    ctx.fill();
  }

  for (const powerup of rt.powerups) {
    if (!powerup.alive) continue;
    drawPowerup(ctx, powerup);
  }

  for (const shot of rt.shots) {
    const sx = shot.vx >= 0 ? shot.x : shot.x - 18;
    ctx.fillStyle = "#ffd166";
    roundRect(ctx, sx, shot.y, 18, 4, 2);
    ctx.fill();
    ctx.strokeStyle = "#edf2f4";
    ctx.lineWidth = 1;
    roundRect(ctx, sx, shot.y, 18, 4, 2);
    ctx.stroke();
  }

  for (const enemy of rt.enemies) {
    ctx.fillStyle = "#fb8500";
    roundRect(ctx, enemy.rect.x, enemy.rect.y, enemy.rect.w, enemy.rect.h, 8);
    ctx.fill();
    ctx.strokeStyle = "#edf2f4";
    ctx.lineWidth = 1;
    roundRect(ctx, enemy.rect.x, enemy.rect.y, enemy.rect.w, enemy.rect.h, 8);
    ctx.stroke();

    ctx.fillStyle = "#02050d";
    ctx.beginPath();
    ctx.arc(enemy.rect.x + 8, enemy.rect.y + 10, 2, 0, Math.PI * 2);
    ctx.arc(enemy.rect.x + enemy.rect.w - 8, enemy.rect.y + 10, 2, 0, Math.PI * 2);
    ctx.fill();
  }

  if (rt.boss) {
    const b = rt.boss.rect;
    ctx.fillStyle = "#ff4d6d";
    roundRect(ctx, b.x, b.y, b.w, b.h, 10);
    ctx.fill();
    ctx.strokeStyle = "#edf2f4";
    ctx.lineWidth = 2;
    roundRect(ctx, b.x, b.y, b.w, b.h, 10);
    ctx.stroke();

    const hw = 120;
    const hx = b.x + b.w / 2 - hw / 2;
    const hy = b.y - 16;
    ctx.fillStyle = "#2e1316";
    roundRect(ctx, hx, hy, hw, 10, 4);
    ctx.fill();
    const fw = hw * (rt.boss.hp / rt.boss.maxHp);
    ctx.fillStyle = "#fb8500";
    roundRect(ctx, hx, hy, fw, 10, 4);
    ctx.fill();

    ctx.fillStyle = "#ff4d6d";
    ctx.font = "bold 10px Trebuchet MS, Segoe UI, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("BOSS", b.x + b.w / 2, hy - 6);
    ctx.textAlign = "left";
  }

  const showPlayer = rt.invulnT === 0 || Math.floor((rt.invulnT * 1000) / 70) % 2 === 0;
  if (showPlayer) {
    let color = "#4cc9f0";
    if (rt.hitFlashT > 0 && Math.floor((rt.hitFlashT * 1000) / 45) % 2 === 0) {
      color = "#ff5d73";
    } else if (rt.starT > 0) {
      color = Math.floor(performance.now() / 90) % 2 === 0 ? "#ffd166" : "#fb8500";
    } else if (rt.blaster) {
      color = "#fb8500";
    }

    ctx.fillStyle = color;
    roundRect(ctx, rt.player.x, rt.player.y, rt.player.w, rt.player.h, 8);
    ctx.fill();
    ctx.strokeStyle = "#edf2f4";
    ctx.lineWidth = 1;
    roundRect(ctx, rt.player.x, rt.player.y, rt.player.w, rt.player.h, 8);
    ctx.stroke();

    const ex = rt.facing >= 0 ? rt.player.x + rt.player.w - 10 : rt.player.x + 10;
    ctx.fillStyle = "#02050d";
    ctx.beginPath();
    ctx.arc(ex, rt.player.y + 12, 2, 0, Math.PI * 2);
    ctx.fill();

    if (rt.blaster) {
      const bx = rt.facing >= 0 ? rt.player.x + rt.player.w - 2 : rt.player.x - 10;
      ctx.fillStyle = "#edf2f4";
      roundRect(ctx, bx, rt.player.y + rt.player.h / 2 - 5, 12, 10, 3);
      ctx.fill();
    }
  }

  drawHud(ctx, rt);

  if (rt.paused || rt.gameOver) {
    ctx.fillStyle = "rgba(0,0,0,0.62)";
    ctx.fillRect(0, 0, W, H);

    if (rt.paused) {
      ctx.fillStyle = "#edf2f4";
      ctx.font = "bold 56px Trebuchet MS, Segoe UI, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("PAUSED", W / 2, H / 2 - 20);
      ctx.fillStyle = "#8d99ae";
      ctx.font = "15px Trebuchet MS, Segoe UI, sans-serif";
      ctx.fillText("P resume | R restart | N select", W / 2, H / 2 + 18);
      ctx.textAlign = "left";
      return;
    }

    ctx.fillStyle = "#ff4d6d";
    ctx.font = "bold 54px Trebuchet MS, Segoe UI, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("GAME OVER", W / 2, H / 2 - 30);

    ctx.fillStyle = "#edf2f4";
    ctx.font = "24px Trebuchet MS, Segoe UI, sans-serif";
    ctx.fillText(`Final Score: ${rt.score}`, W / 2, H / 2 + 12);

    if (rt.newBest) {
      ctx.fillStyle = "#ffd166";
      ctx.font = "bold 15px Trebuchet MS, Segoe UI, sans-serif";
      ctx.fillText("NEW BEST", W / 2, H / 2 + 42);
    }

    ctx.fillStyle = "#8d99ae";
    ctx.font = "14px Trebuchet MS, Segoe UI, sans-serif";
    ctx.fillText("R restart | N select | Q menu", W / 2, H / 2 + 72);
    ctx.textAlign = "left";
  }
}

function drawSelect(ctx: CanvasRenderingContext2D, sel: number): void {
  ctx.fillStyle = "#edf2f4";
  ctx.font = "bold 52px Trebuchet MS, Segoe UI, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText("ENDLESS METRO RUN", W / 2, 132);

  ctx.fillStyle = "#8d99ae";
  ctx.font = "18px Trebuchet MS, Segoe UI, sans-serif";
  ctx.fillText("Choose Difficulty", W / 2, 178);

  for (let i = 0; i < DIFFICULTIES.length; i += 1) {
    const d = DIFFICULTIES[i] as Difficulty;
    const x = (W - 360) / 2;
    const y = 260 + i * 96;
    const selected = i === sel;

    ctx.fillStyle = selected ? "#1b3556" : "#111c31";
    roundRect(ctx, x, y, 360, 72, 12);
    ctx.fill();

    ctx.strokeStyle = selected ? "#4cc9f0" : "#2b436a";
    ctx.lineWidth = selected ? 2 : 1;
    roundRect(ctx, x, y, 360, 72, 12);
    ctx.stroke();

    ctx.fillStyle = selected ? "#edf2f4" : "#c4d2e8";
    ctx.font = "bold 24px Trebuchet MS, Segoe UI, sans-serif";
    ctx.fillText(d.name, W / 2, y + 34);

    ctx.fillStyle = "#8d99ae";
    ctx.font = "12px Trebuchet MS, Segoe UI, sans-serif";
    ctx.fillText(`${d.baseSpeed.toFixed(1)} base speed`, W / 2, y + 54);
  }

  ctx.fillStyle = "#8d99ae";
  ctx.font = "13px Trebuchet MS, Segoe UI, sans-serif";
  ctx.fillText("Up/Down select | Enter start | Q menu", W / 2, H - 24);
  ctx.textAlign = "left";
}

function drawHud(ctx: CanvasRenderingContext2D, rt: Runtime): void {
  ctx.fillStyle = "rgba(15,24,41,0.92)";
  roundRect(ctx, 16, 14, 508, 62, 10);
  ctx.fill();
  ctx.strokeStyle = "#2b436a";
  ctx.lineWidth = 1;
  roundRect(ctx, 16, 14, 508, 62, 10);
  ctx.stroke();

  ctx.fillStyle = "#ffd166";
  ctx.font = "bold 18px Trebuchet MS, Segoe UI, sans-serif";
  ctx.fillText(`Score: ${rt.score}`, 28, 38);

  ctx.fillStyle = "#4cc9f0";
  ctx.fillText(`Best: ${Math.max(rt.best, rt.score)}`, 170, 38);

  let lx = 318;
  for (let i = 0; i < rt.lives; i += 1) {
    const hx = lx + i * 22;
    const hy = 34;
    ctx.fillStyle = "#ff5d73";
    ctx.beginPath();
    ctx.arc(hx - 4, hy - 2, 5, 0, Math.PI * 2);
    ctx.arc(hx + 4, hy - 2, 5, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.moveTo(hx - 5, hy);
    ctx.lineTo(hx + 5, hy);
    ctx.lineTo(hx, hy + 8);
    ctx.closePath();
    ctx.fill();
  }

  ctx.fillStyle = "#b98cff";
  ctx.font = "bold 16px Trebuchet MS, Segoe UI, sans-serif";
  ctx.fillText(rt.d.name, 458, 38);

  ctx.fillStyle = "#8d99ae";
  ctx.font = "12px Trebuchet MS, Segoe UI, sans-serif";
  ctx.fillText(powerStatus(rt), 28, 58);

  ctx.fillStyle = "#8d99ae";
  ctx.font = "13px Trebuchet MS, Segoe UI, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText("Space/^ jump | Shift run | F/Ctrl shoot | P pause | R restart | N select | Q menu", W / 2, H - 24);
  ctx.textAlign = "left";
}

function drawPowerup(ctx: CanvasRenderingContext2D, pu: Powerup): void {
  const x = pu.x;
  const y = pu.y;

  if (pu.type === "shield") {
    ctx.fillStyle = "#4cc9f0";
    ctx.beginPath();
    ctx.arc(x, y, 10, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = "#edf2f4";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.arc(x, y, 10, 0, Math.PI * 2);
    ctx.stroke();
    return;
  }

  if (pu.type === "double") {
    ctx.fillStyle = "#9b5de5";
    roundRect(ctx, x - 9, y - 9, 18, 18, 4);
    ctx.fill();
    ctx.fillStyle = "#edf2f4";
    ctx.font = "bold 10px Trebuchet MS, Segoe UI, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("x2", x, y + 3);
    ctx.textAlign = "left";
    return;
  }

  if (pu.type === "jump") {
    ctx.fillStyle = "#56d36c";
    ctx.beginPath();
    ctx.moveTo(x, y - 10);
    ctx.lineTo(x + 10, y);
    ctx.lineTo(x, y + 10);
    ctx.lineTo(x - 10, y);
    ctx.closePath();
    ctx.fill();
    return;
  }

  if (pu.type === "star") {
    ctx.fillStyle = "#ffd166";
    ctx.beginPath();
    ctx.moveTo(x, y - 12);
    ctx.lineTo(x + 5, y - 3);
    ctx.lineTo(x + 13, y - 3);
    ctx.lineTo(x + 7, y + 4);
    ctx.lineTo(x + 10, y + 12);
    ctx.lineTo(x, y + 7);
    ctx.lineTo(x - 10, y + 12);
    ctx.lineTo(x - 7, y + 4);
    ctx.lineTo(x - 13, y - 3);
    ctx.lineTo(x - 5, y - 3);
    ctx.closePath();
    ctx.fill();
    return;
  }

  ctx.fillStyle = "#fb8500";
  roundRect(ctx, x - 11, y - 6, 22, 12, 4);
  ctx.fill();
  ctx.strokeStyle = "#edf2f4";
  ctx.lineWidth = 1;
  roundRect(ctx, x - 11, y - 6, 22, 12, 4);
  ctx.stroke();
  roundRect(ctx, x + 10, y - 2, 6, 4, 2);
  ctx.fillStyle = "#edf2f4";
  ctx.fill();
}

function powerStatus(rt: Runtime): string {
  const parts: string[] = [];
  if (rt.shields > 0) parts.push(`Shield:${rt.shields}`);
  if (rt.doubleT > 0) parts.push("2xScore");
  if (rt.jumpBoostT > 0) parts.push("Jump+");
  if (rt.blaster) parts.push("Blaster");
  if (rt.starT > 0) parts.push("Star");
  if (parts.length === 0) return "No Powerups";
  return parts.join("  ");
}

function rectOverlap(a: Rect, b: Rect): boolean {
  return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
}

function inflateRect(r: Rect, x: number, y: number): Rect {
  return {
    x: r.x - x / 2,
    y: r.y - y / 2,
    w: r.w + x,
    h: r.h + y
  };
}

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number): void {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function randomInt(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function randomRange(min: number, max: number): number {
  return min + Math.random() * (max - min);
}

function pick<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)] as T;
}

function readBestScore(): number {
  const raw = window.localStorage.getItem("arcade.endless_metro_run.best");
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : 0;
}

function writeBestScore(score: number): void {
  window.localStorage.setItem("arcade.endless_metro_run.best", String(score));
}

export default EndlessMetroRunGame;
