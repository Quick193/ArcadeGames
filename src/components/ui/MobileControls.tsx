import { useEffect, useRef } from "react";
import "./mobile-controls.css";

export interface ControlButton {
  label: string;
  onPress: () => void;
  repeat?: boolean;
}

interface MobileControlsProps {
  dpad?: {
    up?: () => void;
    down?: () => void;
    left?: () => void;
    right?: () => void;
  };
  actions?: ControlButton[];
}

function MobileControls({ dpad, actions = [] }: MobileControlsProps) {
  const holdDelayRef = useRef<number | null>(null);
  const holdIntervalRef = useRef<number | null>(null);

  const stopHold = () => {
    if (holdDelayRef.current != null) {
      window.clearTimeout(holdDelayRef.current);
      holdDelayRef.current = null;
    }
    if (holdIntervalRef.current != null) {
      window.clearInterval(holdIntervalRef.current);
      holdIntervalRef.current = null;
    }
  };

  const startHold = (onPress: () => void, repeat: boolean) => {
    onPress();
    if (!repeat) {
      return;
    }
    stopHold();
    holdDelayRef.current = window.setTimeout(() => {
      holdIntervalRef.current = window.setInterval(onPress, 90);
    }, 220);
  };

  const bind = (onPress: (() => void) | undefined, repeat = false) => ({
    onPointerDown: () => {
      if (!onPress) return;
      startHold(onPress, repeat);
    },
    onPointerUp: stopHold,
    onPointerLeave: stopHold,
    onPointerCancel: stopHold
  });

  useEffect(() => stopHold, []);

  return (
    <section className="mobile-controls" aria-label="Mobile controls">
      {dpad && (
        <div className="mobile-dpad">
          <button type="button" className="ctrl ctrl-up" {...bind(dpad.up, true)} disabled={!dpad.up}>↑</button>
          <button type="button" className="ctrl ctrl-left" {...bind(dpad.left, true)} disabled={!dpad.left}>←</button>
          <button type="button" className="ctrl ctrl-down" {...bind(dpad.down, true)} disabled={!dpad.down}>↓</button>
          <button type="button" className="ctrl ctrl-right" {...bind(dpad.right, true)} disabled={!dpad.right}>→</button>
        </div>
      )}

      {actions.length > 0 && (
        <div className="mobile-actions">
          {actions.map((action) => (
            <button key={action.label} type="button" className="ctrl action" {...bind(action.onPress, Boolean(action.repeat))}>
              {action.label}
            </button>
          ))}
        </div>
      )}
    </section>
  );
}

export default MobileControls;
