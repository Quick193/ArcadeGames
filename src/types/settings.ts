export type ControlScheme = "buttons" | "gestures";

export interface AppSettings {
  music_volume: number;
  sfx_volume: number;
  music_enabled: boolean;
  sfx_enabled: boolean;
  theme: string;
  show_particles: boolean;
  show_bg_anim: boolean;
  show_fps: boolean;
  fps_cap: number;
  show_ghost_piece: boolean;
  auto_clear_annotations: boolean;
  chess_show_hints: boolean;
  mobile_control_scheme: ControlScheme;
}
