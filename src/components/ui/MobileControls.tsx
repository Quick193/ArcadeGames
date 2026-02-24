import "./mobile-controls.css";

export interface ControlButton {
  label: string;
  onPress: () => void;
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
  return (
    <section className="mobile-controls" aria-label="Mobile controls">
      {dpad && (
        <div className="mobile-dpad">
          <button type="button" className="ctrl ctrl-up" onClick={dpad.up} disabled={!dpad.up}>↑</button>
          <button type="button" className="ctrl ctrl-left" onClick={dpad.left} disabled={!dpad.left}>←</button>
          <button type="button" className="ctrl ctrl-down" onClick={dpad.down} disabled={!dpad.down}>↓</button>
          <button type="button" className="ctrl ctrl-right" onClick={dpad.right} disabled={!dpad.right}>→</button>
        </div>
      )}

      {actions.length > 0 && (
        <div className="mobile-actions">
          {actions.map((action) => (
            <button key={action.label} type="button" className="ctrl action" onClick={action.onPress}>
              {action.label}
            </button>
          ))}
        </div>
      )}
    </section>
  );
}

export default MobileControls;
