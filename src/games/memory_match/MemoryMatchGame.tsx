import { useEffect, useMemo, useState } from "react";
import { useGameSession } from "../../services/progression/useGameSession";
import type { ControlScheme } from "../../types/settings";
import "./memory.css";

interface MemoryMatchGameProps {
  onExit: () => void;
  controlScheme: ControlScheme;
}

interface Card {
  value: number;
  flipped: boolean;
  matched: boolean;
}

function MemoryMatchGame({ onExit }: MemoryMatchGameProps) {
  const [cards, setCards] = useState<Card[]>(() => createCards());
  const [first, setFirst] = useState<number | null>(null);
  const [second, setSecond] = useState<number | null>(null);
  const [moves, setMoves] = useState(0);
  const [pairs, setPairs] = useState(0);
  const [errors, setErrors] = useState(0);
  const won = pairs === 8;
  const session = useGameSession("memory_match");
  const exitToMenu = () => {
    session.recordPlaytimeOnly();
    onExit();
  };

  useEffect(() => {
    if (first == null || second == null) return;
    const id = window.setTimeout(() => {
      setCards((prev) => {
        const next = prev.map((c) => ({ ...c }));
        if (next[first].value === next[second].value) {
          next[first].matched = true;
          next[second].matched = true;
          setPairs((p) => p + 1);
        } else {
          next[first].flipped = false;
          next[second].flipped = false;
          setErrors((e) => e + 1);
        }
        return next;
      });
      setFirst(null);
      setSecond(null);
    }, 650);
    return () => window.clearTimeout(id);
  }, [first, second]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "q" || e.key === "Escape") exitToMenu();
      if (e.key === "r") {
        session.restartSession();
        setCards(createCards());
        setFirst(null);
        setSecond(null);
        setMoves(0);
        setPairs(0);
        setErrors(0);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [exitToMenu, session]);

  const score = useMemo(() => Math.max(0, 1000 - moves * 10), [moves]);

  useEffect(() => {
    if (!won) {
      return;
    }
    session.recordResult({
      score,
      won: true,
      extra: { errors }
    });
  }, [errors, score, session, won]);

  return (
    <section className="memory-screen">
      <header className="memory-header">
        <div>
          <h1>Memory Match</h1>
          <p>Find all pairs. R restart, Q menu.</p>
        </div>
        <button type="button" onClick={exitToMenu}>Back to Menu</button>
      </header>

      <div className="memory-stats">
        <span>Moves: {moves}</span>
        <span>Pairs: {pairs}/8</span>
        <span>Errors: {errors}</span>
        <span>Score: {score}</span>
      </div>

      <div className="memory-grid">
        {cards.map((card, i) => (
          <button
            key={`${card.value}-${i}`}
            type="button"
            className={`m-card ${card.matched ? "matched" : ""} ${card.flipped ? "flipped" : ""}`}
            disabled={card.flipped || card.matched || first != null && second != null || won}
            onClick={() => {
              setCards((prev) => {
                const next = prev.map((c) => ({ ...c }));
                next[i].flipped = true;
                return next;
              });
              if (first == null) setFirst(i);
              else if (second == null && i !== first) {
                setSecond(i);
                setMoves((m) => m + 1);
              }
            }}
          >
            {card.flipped || card.matched ? card.value + 1 : "•"}
          </button>
        ))}
      </div>

      {won && <div className="memory-win">MATCH COMPLETE</div>}
    </section>
  );
}

function createCards(): Card[] {
  const values = [...Array(8).keys(), ...Array(8).keys()];
  for (let i = values.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [values[i], values[j]] = [values[j], values[i]];
  }
  return values.map((v) => ({ value: v, flipped: false, matched: false }));
}

export default MemoryMatchGame;
