'use client';
import {useEffect,useRef,useState} from 'react';

type Review={version:number;rating:'unreviewed'|'again'|'developing'|'confident';reviewed_at:string|null};
type Card={id:string;topic:string;prompt:string;passages:{text:string;student_edited:boolean}[];sources:{id:string;text:string;label?:string;segment_number?:number;start_sample?:number;sample_rate?:number}[];review:Review};
type Deck={revision_id:string|null;cards:Card[];omitted:number;issues:unknown[]};
const labels={unreviewed:'Not reviewed',again:'Needs review',developing:'Developing',confident:'Confident'};

function RecallCard({card,revision,lecture,csrf,onSaved}:{card:Card;revision:string;lecture:string;csrf:string;onSaved:(review:Review)=>void}){
  const [revealed,setRevealed]=useState(false),[draft,setDraft]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState(''),[saved,setSaved]=useState('');
  const [pending,setPending]=useState<{key:string;rating:Review['rating']}|null>(null);
  const [conflict,setConflict]=useState(false);
  const alive=useRef(true);
  useEffect(()=>{alive.current=true;return()=>{alive.current=false;};},[]);
  async function rate(rating:Review['rating']){
    const command=pending??{key:crypto.randomUUID(),rating};setPending(command);setBusy(true);setError('');setSaved('');
    try{
      const response=await fetch(`/api/lectures/${lecture}/study/learning/reviews`,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf,'Idempotency-Key':command.key},body:JSON.stringify({revision_id:revision,block_id:card.id,expected_version:card.review.version,rating:command.rating})});
      const data=await response.json();if(!alive.current)return;
      if(!response.ok){if(response.status===409){setConflict(true);setPending(null);}throw new Error(data.error?.message||'Could not save your assessment.');}
      setPending(null);setSaved('Assessment saved.');onSaved(data);
    }catch(e){if(alive.current)setError(e instanceof Error?e.message:'Could not save your assessment.');}
    finally{if(alive.current)setBusy(false);}
  }
  return <article className="catchup-item learning-card">
    <h4>{card.topic}</h4><p className="study-text">{card.prompt}</p>
    <label>Practice answer (optional)<textarea value={draft} onChange={e=>setDraft(e.target.value)} rows={4} placeholder="Try recalling the explanation before revealing your notes."/></label>
    <p className="small muted">This scratch answer stays only while this card is open. It is not saved or graded.</p>
    <button className="secondary" aria-expanded={revealed} onClick={()=>setRevealed(!revealed)}>{revealed?'Hide answer':'Reveal saved answer'}</button>
    {revealed&&<div><h4>Answer from saved notes</h4>{card.passages.map((p,i)=><div key={i}>{p.student_edited&&<p className="small muted">Your edited note · not independently verified</p>}<p className="study-text">{p.text}</p></div>)}
      <div className="study-sources">{card.sources.map(source=><details key={source.id}><summary>{source.label||`Source · recording ${source.segment_number}, ${Math.floor((source.start_sample??0)/(source.sample_rate??1))} seconds`}</summary><p className="study-text">{source.text}</p></details>)}</div>
      <p>How well did you recall this?</p><div className="editor-actions">{(['again','developing','confident'] as const).map(rating=><button className="secondary" key={rating} disabled={busy||!!pending||conflict} onClick={()=>void rate(rating)}>{labels[rating]}</button>)}<button className="text-button" disabled={busy||!!pending||conflict||card.review.rating==='unreviewed'} onClick={()=>void rate('unreviewed')}>Reset assessment</button></div>
    </div>}
    <p className="small muted">Self-assessment: {labels[card.review.rating]}{card.review.reviewed_at?` · ${new Date(card.review.reviewed_at).toLocaleString()}`:''}</p>
    {saved&&<p role="status">{saved}</p>}{error&&<p className="error" role="alert">{error}</p>}{pending&&!busy&&<button className="secondary" onClick={()=>void rate(pending.rating)}>Retry saving assessment</button>}
  </article>;
}

export default function LearningTools({lecture,csrf}:{lecture:string;csrf:string}){
  const [deck,setDeck]=useState<Deck|null>(null),[error,setError]=useState(''),[loading,setLoading]=useState(true),[refresh,setRefresh]=useState(0);
  const [filter,setFilter]=useState('all'),[topic,setTopic]=useState(''),[index,setIndex]=useState(0);
  useEffect(()=>{
    const controller=new AbortController();
    void (async()=>{try{const response=await fetch(`/api/lectures/${lecture}/study/learning`,{cache:'no-store',signal:controller.signal});const data=await response.json();if(!response.ok)throw new Error(data.error?.message||'Could not load practice.');if(!controller.signal.aborted){setDeck(data);setIndex(0);}}
      catch(e){if(!controller.signal.aborted)setError(e instanceof Error?e.message:'Could not load practice.');}finally{if(!controller.signal.aborted)setLoading(false);}})();
    return()=>controller.abort();
  },[lecture,refresh]);
  const cards=(deck?.cards??[]).filter(c=>(filter==='all'||c.review.rating!=='confident')&&c.topic.toLowerCase().includes(topic.toLowerCase()));
  const position=Math.min(index,Math.max(0,cards.length-1)),card=cards[position];
  return <section className="learning-tools" aria-label="Recall practice"><h3>Recall practice</h3>
    <p>Use flashcards or write a practice answer, then compare with your saved notes. These topic prompts reuse complete note sections without another model request.</p>
    <p className="small muted">Self-assessments help you choose what to revisit; they are not a mastery score. Check the sources before relying on an answer. New note revisions start with fresh assessments.</p>
    <div className="study-actions"><label>Practice focus<select value={filter} onChange={e=>{setFilter(e.target.value);setIndex(0);}}><option value="all">All topics</option><option value="review">Needs practice (including unreviewed)</option></select></label><label>Find a topic<input value={topic} onChange={e=>{setTopic(e.target.value);setIndex(0);}}/></label><button className="secondary" disabled={loading} onClick={()=>{setLoading(true);setError('');setRefresh(refresh+1);}}>Refresh practice</button></div>
    <p className="small muted">Changing cards, filters or refreshing clears the scratch answer. Saved assessments remain.</p>
    {loading&&<p role="status">Loading practice…</p>}{error&&<p className="error" role="alert">{error}</p>}
    {deck&&<><p>{deck.cards.filter(c=>c.review.rating==='confident').length} of {deck.cards.length} topics self-rated confident.</p>{deck.revision_id&&<details className="small muted"><summary>Practice source revision</summary><p className="study-text">{deck.revision_id}</p><p>Practice stays on this saved revision until you refresh. Source changes are checked again when you save an assessment.</p></details>}{(deck.omitted>0||deck.issues.length>0)&&<p className="inline-notice">{deck.omitted>0?`${deck.omitted} sections omitted because they use changed, missing, uncited or visual evidence. `:''}{deck.issues.length>0?'Saved notes or transcript have source warnings. Review them in Study notes and Transcript.':''}</p>}
      {!deck.cards.length&&<p>No eligible recall cards yet. Save source-linked notes first; review or regenerate notes after source corrections.</p>}
      {!!deck.cards.length&&!cards.length&&<p>No topics match this focus. Choose All topics or clear the search.</p>}
      {card&&deck.revision_id&&!loading&&<><div className="editor-actions"><button className="secondary" disabled={position===0} onClick={()=>setIndex(position-1)}>Previous card</button><span>Card {position+1} of {cards.length}</span><button className="secondary" disabled={position>=cards.length-1} onClick={()=>setIndex(position+1)}>Next card</button></div><RecallCard key={`${refresh}:${deck.revision_id}:${card.id}:${filter}:${topic}`} card={card} revision={deck.revision_id} lecture={lecture} csrf={csrf} onSaved={review=>setDeck(current=>current?{...current,cards:current.cards.map(c=>c.id===card.id?{...c,review}:c)}:current)}/></>}
    </>}
  </section>;
}
