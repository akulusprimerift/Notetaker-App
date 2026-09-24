'use client';
import {useEffect,useState} from 'react';
export default function Theme(){
  const [theme,setTheme]=useState('light');
  useEffect(()=>{let value='light';try{const saved=localStorage.getItem('notetaker:theme');if(saved&&['light','dark','pink','blue'].includes(saved))value=saved;}catch{}setTheme(value);document.documentElement.dataset.theme=value;void window.desktopApp?.appearance?.(value).catch(()=>{});},[]);
  function change(value:string){void window.desktopApp?.appearance?.(value).catch(()=>{});setTheme(value);document.documentElement.dataset.theme=value;try{localStorage.setItem('notetaker:theme',value);}catch{}}
  return <label className="theme-choice">Theme <select aria-label="App theme" value={theme} onChange={event=>change(event.target.value)}><option value="light">Slate</option><option value="dark">Midnight</option><option value="pink">Pink</option><option value="blue">Blue</option></select></label>;
}
