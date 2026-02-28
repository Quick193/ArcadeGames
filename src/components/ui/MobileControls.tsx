import { useEffect, useRef, type DragEvent, type MouseEvent, type PointerEvent, type SyntheticEvent } from "react";
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
    onPointerDown: (event: PointerEvent<HTMLButtonElement>) => {
      if (!onPress) return;
      event.preventDefault();
      if (event.currentTarget.setPointerCapture) {
        event.currentTarget.setPointerCapture(event.pointerId);
      }
      startHold(onPress, repeat);
    },
    onPointerUp: (event: PointerEvent<HTMLButtonElement>) => {
      event.preventDefault();
      if (event.currentTarget.releasePointerCapture && event.currentTarget.hasPointerCapture(event.pointerId)) {
        event.currentTarget.releasePointerCapture(event.pointerId);
      }
      stopHold();
    },
    onPointerMove: (event: PointerEvent<HTMLButtonElement>) => {
      event.preventDefault();
    },
    onPointerLeave: stopHold,
    onPointerCancel: stopHold,
    onDragStart: (event: DragEvent<HTMLButtonElement>) => event.preventDefault(),
    onSelectStart: (event: SyntheticEvent<HTMLButtonElement>) => event.preventDefault(),
    onContextMenu: (event: MouseEvent<HTMLButtonElement>) => event.preventDefault()
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
