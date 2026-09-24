'use client';
import {useRef,useState} from 'react';
const prompt='Use only the attached lecture notes as your source. Help me study by asking one question at a time, waiting for my answer, then explaining corrections with the relevant section and source timestamp. Cover definitions, worked examples, qualifications and emphasized ideas. Do not invent missing information. Say when the notes do not support an answer. Start with five recall questions, then give me a worked-example exercise.';
export default function ExportNotes({url,label='Selected saved revision'}:{url:string;label?:string}){
  const dialog=useRef<HTMLDialogElement>(null);
  const [copied,setCopied]=useState('');
  return <div className="export-actions" aria-label={label+' exports'}>
    <a className="primary" href={url}>Export Markdown ↓</a>
    <button className="secondary" onClick={()=>dialog.current?.showModal()}>How to use your notes</button>
    <details><summary>More formats</summary><a className="secondary" href={url+'?format=docx'}>Word (.docx)</a><a className="secondary" href={url+'?format=pptx'}>Study slides (.pptx)</a><a className="secondary" href={url+'?format=html'}>Web page / print to PDF</a><a className="secondary" href={url+'?format=txt'}>Plain text</a></details>
    <span className="small muted">{label} · save edits before exporting</span>
    <dialog ref={dialog} className="accounts-dialog export-help" aria-label="Study with exported notes">
      <div className="accounts-heading"><h2>Take your notes with you</h2><button className="secondary" onClick={()=>dialog.current?.close()}>Close</button></div>
      <ol><li>Save your edits, then export the revision you want. Finish → Finalize lecture creates a permanent snapshot after processing.</li><li>Markdown (.md) is a text file with headings and source references. Open it in a Markdown editor or any text editor, or upload it to a study tool that accepts Markdown.</li><li>Word is editable in a compatible document app. Study slides paginate all saved text, including references; they are a reading deck, not an AI summary. HTML includes supported diagrams and can be printed to PDF from your browser. Other formats retain diagram descriptions as text.</li><li>If you choose an external AI study tool, upload your export there and paste the instructions below. Check its answers against your notes and citations. Uploading shares that file with the service you choose.</li></ol>
      <h3>Try this study prompt</h3><pre>{prompt}</pre><button className="secondary" onClick={()=>void navigator.clipboard.writeText(prompt).then(()=>setCopied('Copied.')).catch(()=>setCopied('Select and copy the prompt above.'))}>Copy study prompt</button><p role="status">{copied}</p>
      <p>Change the prompt to request flashcards, a practice exam, a revision plan or a step-by-step explanation. Local source IDs and timestamps stay in the export; audio files are not included.</p>
    </dialog>
  </div>;
}
