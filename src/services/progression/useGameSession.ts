import { useRef } from "react";
import type { GameId } from "../../types/game";
import { addSessionPlaytime, recordGameResult, type RecordGameInput } from "./progressionService";

export function useGameSession(gameId: GameId) {
  const startedAtRef = useRef(performance.now());
  const recordedRef = useRef(false);

  const restartSession = () => {
    startedAtRef.current = performance.now();
    recordedRef.current = false;
  };

  const durationSec = () => Math.max(0, (performance.now() - startedAtRef.current) / 1000);

  const recordResult = (input: Omit<RecordGameInput, "gameId" | "durationSec">) => {
    if (recordedRef.current) {
      return;
    }
    recordGameResult({
      gameId,
      score: input.score,
      won: input.won,
      extra: input.extra,
      durationSec: durationSec()
    });
    recordedRef.current = true;
  };

  const recordPlaytimeOnly = () => {
    if (recordedRef.current) {
      return;
    }
    addSessionPlaytime(gameId, durationSec());
    recordedRef.current = true;
  };

  return {
    restartSession,
    recordResult,
    recordPlaytimeOnly
  };
}
