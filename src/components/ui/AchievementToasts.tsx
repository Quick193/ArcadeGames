interface ToastItem {
  key: string;
  name: string;
  points: number;
  color: string;
}

interface AchievementToastsProps {
  items: ToastItem[];
}

function AchievementToasts({ items }: AchievementToastsProps) {
  if (items.length === 0) {
    return null;
  }

  return (
    <div className="ach-toast-stack" aria-live="polite" aria-atomic="false">
      {items.map((item) => (
        <div key={item.key} className="ach-toast" style={{ borderColor: item.color }}>
          <strong>Achievement Unlocked</strong>
          <span>{item.name}</span>
          <small>{item.points} pts</small>
        </div>
      ))}
    </div>
  );
}

export default AchievementToasts;
