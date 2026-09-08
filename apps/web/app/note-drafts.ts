export type Draft = {id:string;lecture:string;base_id:string;expected_version:number;passages:Record<string,string>;topics:Record<string,string>;base_passages?:Record<string,string>;base_topics?:Record<string,string>;additional_text:string;updated:number;save_key:string};

async function database():Promise<IDBDatabase>{
  return new Promise((resolve,reject)=>{
    const request=indexedDB.open('notetaker-note-drafts',1);
    request.onupgradeneeded=()=>request.result.createObjectStore('drafts',{keyPath:'id'});
    request.onsuccess=()=>resolve(request.result);
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
export const saveDraft=(draft:Draft)=>transact('readwrite',store=>store.put(draft));
export const deleteDraft=(id:string)=>transact('readwrite',store=>store.delete(id));
