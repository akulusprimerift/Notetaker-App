'use client';

type Tab<T extends string>={id:T;label:string;description:string};

export default function LectureNavigation<T extends string>({tabs,selected,lectureId,kind}:{tabs:ReadonlyArray<Tab<T>>;selected:T;lectureId:string;kind:'primary'|'secondary'}){
  return <nav className={kind==='primary'?'lecture-primary-nav':'lecture-secondary-nav'} aria-label={kind==='primary'?'Main lecture sections':'Other lecture sections'}>
    {tabs.map(tab=><a key={tab.id} href={`#lecture/${lectureId}/${tab.id}`} title={tab.description} aria-current={selected===tab.id?'page':undefined} className={selected===tab.id?'active':''}>{tab.label}</a>)}
  </nav>;
}
