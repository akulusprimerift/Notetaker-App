'use client';
import {useEffect,useState} from 'react';
export default function Theme(){
  const [theme,setTheme]=useState('light');
  useEffect(()=>{try{const saved=localStorage.getItem('notetaker:theme');if(saved==='dark'){setTheme(saved);document.documentElement.dataset.theme=saved;}}catch{}},[]);
  function change(value:string){setTheme(value);document.documentElement.dataset.theme=value;try{localStorage.setItem('notetaker:theme',value);}catch{}}
  return <label className="theme-choice">Theme <select aria-label="App theme" value={theme} onChange={event=>change(event.target.value)}><option value="light">Slate</option><option value="dark">Midnight</option></select></label>;
}
