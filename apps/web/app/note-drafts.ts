export type Draft = {id:string;lecture:string;base_id:string;expected_version:number;passages:Record<string,string>;topics:Record<string,string>;base_passages?:Record<string,string>;base_topics?:Record<string,string>;additional_text:string;updated:number;save_key:string};

async function database():Promise<IDBDatabase>{
  return new Promise((resolve,reject)=>{
    const request=indexedDB.open('notetaker-note-drafts',2);
    request.onupgradeneeded=()=>{if(!request.result.objectStoreNames.contains('drafts'))request.result.createObjectStore('drafts',{keyPath:'id'});request.result.createObjectStore('removed');};
    request.onsuccess=()=>{request.result.onversionchange=()=>request.result.close();resolve(request.result)};
    request.onblocked=()=>reject(new Error('Close older workspace tabs to update local draft storage.'));
    request.onerror=()=>reject(request.error);
  });
}

async function transact<T>(mode:IDBTransactionMode,action:(store:IDBObjectStore)=>IDBRequest<T>):Promise<T>{
  const db=await database();
  return new Promise((resolve,reject)=>{
    const tx=db.transaction('drafts',mode),request=action(tx.objectStore('drafts'));
    tx.oncomplete=()=>{db.close();resolve(request.result)};
    tx.onabort=()=>{db.close();reject(tx.error??new Error('Local draft storage failed.'))};
    tx.onerror=()=>{db.close();reject(tx.error??new Error('Local draft storage failed.'))};
  });
}

export async function drafts(lecture:string){
  return (await transact<Draft[]>('readonly',store=>store.getAll())).filter(d=>d.lecture===lecture).sort((a,b)=>b.updated-a.updated);
}
export async function saveDraft(draft:Draft){
  const db=await database();
  return new Promise<void>((resolve,reject)=>{
    const tx=db.transaction(['drafts','removed'],'readwrite');
    tx.objectStore('removed').get(draft.lecture).onsuccess=event=>{
      if((event.target as IDBRequest).result){tx.abort();return;}
      tx.objectStore('drafts').put(draft);
    };
    tx.oncomplete=()=>{db.close();resolve()};tx.onabort=()=>{db.close();reject(new Error('This lecture was deleted; its draft cannot be restored.'))};
  });
}
export async function purgeDrafts(lecture:string){
  const db=await database();
  return new Promise<void>((resolve,reject)=>{
    const tx=db.transaction(['drafts','removed'],'readwrite');
    tx.objectStore('removed').put(true,lecture);
    tx.objectStore('drafts').openCursor().onsuccess=event=>{const cursor=(event.target as IDBRequest<IDBCursorWithValue|null>).result;if(cursor){if(cursor.value.lecture===lecture)cursor.delete();cursor.continue()}};
    tx.oncomplete=()=>{db.close();resolve()};tx.onabort=()=>{db.close();reject(tx.error)};
  });
}
export const deleteDraft=(id:string)=>transact('readwrite',store=>store.delete(id));
