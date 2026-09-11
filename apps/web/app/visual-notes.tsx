'use client';

import {useCallback,useEffect,useId,useMemo,useState} from 'react';

type Node={id:string;label:string};
type Edge={from:string;to:string;label:string};
type Diagram={caption:string;nodes:Node[];edges:Edge[]};
type Block={id:string;topic:string;kind:string;student_edited?:boolean;diagram?:Diagram;passages:{id:string;text:string;student_edited?:boolean;sources:{source_id:string}[]}[]};
type Revision={id:string;revision:number;student?:boolean;metadata:{model:string};content:{blocks:Block[]}};
type NotesState={revision:Revision|null;editing:{selected:Revision|null}};

function wrap(value:string,max=23){
  const words=value.split(/\s+/).filter(Boolean);const lines:string[]=[];let line='';
  for(const word of words){const next=line?`${line} ${word}`:word;if(next.length>max&&line){lines.push(line);line=word}else line=next;}
  if(line)lines.push(line);return lines.length?lines:[''];
}

function Diagram({diagram}:{diagram:Diagram}){
  const instanceId=useId().replace(/[^a-z0-9]/gi,'');
  const width=Math.max(920,diagram.nodes.length*110),height=Math.max(520,diagram.nodes.length*85);
  const centerX=width/2,centerY=height/2;
  const positions=useMemo(()=>Object.fromEntries(diagram.nodes.map((node,index)=>{
    const angle=(2*Math.PI*index/diagram.nodes.length)-Math.PI/2;
    return [node.id,{x:centerX+(width/2-140)*Math.cos(angle),y:centerY+(height/2-90)*Math.sin(angle)}];
  })),[centerX,centerY,diagram.nodes,height,width]);
  const labels=useMemo(()=>Object.fromEntries(diagram.nodes.map(node=>[node.id,wrap(node.label)])),[diagram.nodes]);
  const titleId=`diagram-${diagram.caption.toLowerCase().replace(/[^a-z0-9]+/g,'-')}-${instanceId}`;
  return <svg className="visual-diagram" viewBox={`0 0 ${width} ${height}`} role="img" aria-labelledby={titleId}>
    <title id={titleId}>{diagram.caption}</title>
    <defs><marker id={`${titleId}-arrow`} markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="currentColor"/></marker></defs>
    <rect width={width} height={height} rx="18" fill="var(--diagram-bg,#f8fafc)"/>
    {diagram.edges.map((edge,index)=>{
      const from=positions[edge.from],to=positions[edge.to];if(!from||!to)return null;
      const dx=to.x-from.x,dy=to.y-from.y,length=Math.hypot(dx,dy),ux=dx/length,uy=dy/length;
      const endX=to.x-ux*Math.min(90/Math.max(Math.abs(ux),.001),40/Math.max(Math.abs(uy),.001));
      const endY=to.y-uy*Math.min(90/Math.max(Math.abs(ux),.001),40/Math.max(Math.abs(uy),.001));
      const labelX=from.x+dx*(.35+.1*(index%3)),labelY=from.y+dy*(.35+.1*(index%3));
      const edgeLines=wrap(edge.label);
      return <g key={`${edge.from}-${edge.to}-${index}`} className="diagram-edge"><line x1={from.x} y1={from.y} x2={endX} y2={endY} markerEnd={`url(#${titleId}-arrow)`}/><rect x={labelX-(Math.max(...edgeLines.map(line=>line.length),1)*7+12)/2} y={labelY-13} width={Math.max(...edgeLines.map(line=>line.length),1)*7+12} height={17*edgeLines.length} rx="4"/><text x={labelX} y={labelY} textAnchor="middle">{edgeLines.map((line,lineIndex)=><tspan key={lineIndex} x={labelX} dy={lineIndex?'16':0}>{line}</tspan>)}</text></g>;
    })}
    {diagram.nodes.map(node=>{const point=positions[node.id],lines=labels[node.id];return <g key={node.id} className="diagram-node"><rect x={point.x-90} y={point.y-40} width="180" height="80" rx="12"/><text x={point.x} y={point.y-(lines.length-1)*8+5} textAnchor="middle">{lines.map((line,index)=><tspan key={index} x={point.x} dy={index?'16':0}>{line}</tspan>)}</text></g>})}
  </svg>;
}

export default function VisualNotes({lecture,onSessionExpired}:{lecture:string;onSessionExpired:()=>void}){
  const [state,setState]=useState<NotesState|null>(null),[error,setError]=useState(''),[loading,setLoading]=useState(true);
  const load=useCallback(async()=>{
    const response=await fetch(`/api/lectures/${encodeURIComponent(lecture)}/notes`,{cache:'no-store'});
    if(response.status===401){onSessionExpired();return;}
    if(!response.ok)throw new Error('Visual notes are unavailable right now.');
    setState(await response.json());setError('');setLoading(false);
  },[lecture,onSessionExpired]);
  useEffect(()=>{
    let alive=true;
    const live=(event:Event)=>{const detail=(event as CustomEvent).detail;if(detail.lecture===lecture){const notes=detail.snapshot.notes;if(alive)setState(notes)}};
    window.addEventListener('lecture-snapshot',live);void load().catch(err=>{if(alive){setError(err instanceof Error?err.message:'Could not load visual notes.');setLoading(false)}});
    const timer=setInterval(()=>void load().catch(err=>{if(alive)setError(err instanceof Error?err.message:'Could not refresh visual notes.')}),5000);
    return()=>{alive=false;clearInterval(timer);window.removeEventListener('lecture-snapshot',live)};
  },[lecture,load]);
  const revision=state?.editing?.selected??state?.revision??null;
  const blocks=revision?.content.blocks.filter(block=>block.diagram)??[];
  return <section className="visual-notes-panel" aria-labelledby="visual-notes-title">
    <div className="section-row"><div><p className="eyebrow">SOURCE-LINKED SCHEMATICS</p><h2 id="visual-notes-title">Visual notes</h2></div><span className="prepared-badge">Safe to inspect</span></div>
    <p className="muted">These diagrams are generated from cited lecture text. They are explanatory schematics, not screenshots of slides or a reconstruction of unread visual information.</p>
    {error&&<p className="error" role="alert">{error}</p>}
    {loading?<p className="page-loading" role="status">Looking for visual explanations…</p>:!revision?<div className="visual-empty"><span aria-hidden="true">◇</span><h3>Visual explanations will appear with your notes.</h3><p>Ask for process diagrams, cycles, or concept maps in your layout instructions, then generate notes from a transcript.</p></div>:!blocks.length?<div className="visual-empty"><span aria-hidden="true">◇</span><h3>No diagram was supported by this lecture yet.</h3><p>Text-only notes are still complete. If a visual explanation is justified, add that request to your note layout prompt and regenerate.</p></div>:<div className="visual-list">{blocks.map(block=>{const diagram=block.diagram!;const sourceIds=[...new Set(block.passages.flatMap(passage=>passage.sources.map(source=>source.source_id)))];return <article className="visual-card" key={block.id}><div className="visual-card-heading"><div><p className="eyebrow">{block.kind}</p><h3>{block.topic}</h3></div>{block.student_edited||block.passages.some(passage=>passage.student_edited)?<span className="prepared-badge">Review after edits</span>:null}</div><Diagram diagram={diagram}/><p className="visual-caption">{diagram.caption}</p><p className="study-text">{diagram.nodes.map(node=>node.label).join(' · ')}{diagram.edges.length?` · ${diagram.edges.map(edge=>`${edge.label}: ${edge.from} → ${edge.to}`).join(' · ')}`:''}</p><p className="small muted">Sources: {sourceIds.join(', ')||'Student addition'}</p></article>})}</div>}
  </section>;
}
