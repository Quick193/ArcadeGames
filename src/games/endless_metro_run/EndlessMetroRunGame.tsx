import { useEffect, useRef, useState } from "react";
import MobileControls from "../../components/ui/MobileControls";
import { useGameSession } from "../../services/progression/useGameSession";
import type { ControlScheme } from "../../types/settings";
import "../neon_blob_dash/runner.css";

const W = 960;
const H = 600;
const GY = 558;

interface EndlessMetroRunGameProps {
  onExit: () => void;
  controlScheme: ControlScheme;
}

function EndlessMetroRunGame({ onExit, controlScheme }: EndlessMetroRunGameProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const frameRef = useRef<number | null>(null);
  const keysRef = useRef<Set<string>>(new Set());

  const [player, setPlayer] = useState({ x: 180, y: GY - 56, vx: 0, vy: 0, w: 42, h: 56 });
  const [speed, setSpeed] = useState(5.2);
  const [obs, setObs] = useState<Array<{ x:number; y:number; w:number; h:number; t:"spike"|"enemy" }>>([]);
  const [coins, setCoins] = useState<Array<{x:number;y:number}>>([]);
  const [score, setScore] = useState(0);
  const [lives, setLives] = useState(3);
  const [dead, setDead] = useState(false);
  const session = useGameSession("endless_metro_run");
  const exitToMenu = () => {
    session.recordPlaytimeOnly();
    onExit();
  };

  const reset = () => {
    session.restartSession();
    setPlayer({ x: 180, y: GY - 56, vx: 0, vy: 0, w: 42, h: 56 });
    setSpeed(5.2); setObs([]); setCoins([]); setScore(0); setLives(3); setDead(false);
  };

  useEffect(() => {
    const kd=(e:KeyboardEvent)=>{
      keysRef.current.add(e.key);
      if(e.key==="q"||e.key==="Escape") exitToMenu();
      if(e.key==="r") reset();
      if((e.key===" "||e.key==="ArrowUp"||e.key==="w") && player.y+player.h>=GY-1 && !dead) setPlayer((p)=>({...p,vy:-15.5}));
      if(e.key==="f"){};
    };
    const ku=(e:KeyboardEvent)=>keysRef.current.delete(e.key);
    window.addEventListener("keydown",kd); window.addEventListener("keyup",ku);
    return ()=>{window.removeEventListener("keydown",kd); window.removeEventListener("keyup",ku);};
  },[dead,exitToMenu,player.y,player.h]);

  useEffect(() => {
    if (!dead) {
      return;
    }
    session.recordResult({
      score: Math.floor(score / 6),
      won: false,
      extra: {
        distance: Math.floor(score / 6)
      }
    });
  }, [dead, score, session]);

  useEffect(()=>{
    const tick=()=>{
      if(!dead){
        setSpeed((s)=>Math.min(9.2,s+0.001));
        setPlayer((p)=>{
          let nx=p.x; let nvy=Math.min(18,p.vy+0.78); let ny=p.y+nvy;
          if(keysRef.current.has("ArrowLeft")||keysRef.current.has("a")) nx-=4;
          if(keysRef.current.has("ArrowRight")||keysRef.current.has("d")) nx+=4;
          nx=Math.max(70,Math.min(W-96,nx));
          if(ny+p.h>=GY){ny=GY-p.h; nvy=0;}
          return {...p,x:nx,y:ny,vy:nvy};
        });

        setObs((prev)=>{
          const moved=prev.map((o)=>({...o,x:o.x-speed})).filter((o)=>o.x+o.w>-80);
          if(Math.random()<0.025) moved.push(Math.random()<0.55?{x:W+30,y:GY-20,w:30,h:20,t:"spike"}:{x:W+30,y:GY-46,w:34,h:34,t:"enemy"});
          const p=player;
          if(moved.some((o)=>overlap(p,o))){
            setLives((l)=>{const nl=l-1; if(nl<=0) setDead(true); return Math.max(0,nl);});
            return moved.filter((o)=>!overlap(p,o));
          }
          return moved;
        });

        setCoins((prev)=>{
          const moved=prev.map((c)=>({...c,x:c.x-speed})).filter((c)=>c.x>-30);
          if(Math.random()<0.02) moved.push({x:W+20,y:GY-[70,90,110][Math.floor(Math.random()*3)]});
          const p=player;
          const keep=[] as typeof moved;
          for(const c of moved){
            if(c.x>=p.x&&c.x<=p.x+p.w&&c.y>=p.y&&c.y<=p.y+p.h){ setScore((s)=>s+10); }
            else keep.push(c);
          }
          return keep;
        });

        setScore((s)=>s+1);
      }

      drawMetro(canvasRef.current,{player,obs,coins,score,lives,dead,speed});
      frameRef.current=requestAnimationFrame(tick);
    };
    frameRef.current=requestAnimationFrame(tick);
    return ()=>{if(frameRef.current!=null)cancelAnimationFrame(frameRef.current);};
  },[coins,dead,lives,obs,player,score,speed]);

  return (
    <section className="runner-screen">
      <header className="runner-header"><div><h1>Endless Metro Run</h1><p>Run, jump, collect coins, survive.</p></div><button type="button" onClick={exitToMenu}>Back to Menu</button></header>
      <canvas ref={canvasRef} className="runner-canvas" width={W} height={H} />
      {controlScheme==="buttons" && <MobileControls dpad={{left:()=>setPlayer((p)=>({...p,x:Math.max(70,p.x-24)})),right:()=>setPlayer((p)=>({...p,x:Math.min(W-96,p.x+24)}))}} actions={[{label:"Jump",onPress:()=>setPlayer((p)=>p.y+p.h>=GY-1?{...p,vy:-15.5}:p)},{label:"Reset",onPress:reset},{label:"Menu",onPress:exitToMenu}]} />}
    </section>
  );
}

function drawMetro(canvas:HTMLCanvasElement|null,s:any){
  if(!canvas)return; const ctx=canvas.getContext("2d"); if(!ctx)return;
  const bg=ctx.createLinearGradient(0,0,0,H); bg.addColorStop(0,"#071327"); bg.addColorStop(1,"#030a14"); ctx.fillStyle=bg; ctx.fillRect(0,0,W,H);
  ctx.fillStyle="#1f2a3f"; ctx.fillRect(0,GY,W,H-GY);
  for(let i=0;i<20;i+=1){ctx.fillStyle="#2f3d59"; ctx.fillRect((i*70+(s.score%70))%W,GY-8,32,4);} 
  ctx.fillStyle="#4cc9f0"; ctx.fillRect(s.player.x,s.player.y,s.player.w,s.player.h);
  for(const o of s.obs){ ctx.fillStyle=o.t==="spike"?"#ff5d73":"#fb8500"; ctx.fillRect(o.x,o.y,o.w,o.h); }
  for(const c of s.coins){ ctx.fillStyle="#ffd166"; ctx.beginPath(); ctx.arc(c.x,c.y,6,0,Math.PI*2); ctx.fill(); }
  ctx.fillStyle="#8d99ae"; ctx.font="bold 18px Trebuchet MS"; ctx.fillText(`Score ${Math.floor(s.score/6)}  Lives ${s.lives}  Speed ${s.speed.toFixed(1)}`,16,28);
  if(s.dead){ ctx.fillStyle="rgba(0,0,0,0.58)"; ctx.fillRect(0,0,W,H); ctx.fillStyle="#ff4d6d"; ctx.font="bold 48px Trebuchet MS"; ctx.textAlign="center"; ctx.fillText("GAME OVER",W/2,H/2); ctx.textAlign="left"; }
}

function overlap(a:any,b:any){ return a.x < b.x+b.w && a.x+a.w > b.x && a.y < b.y+b.h && a.y+a.h > b.y; }

export default EndlessMetroRunGame;
