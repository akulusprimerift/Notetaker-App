export {};

declare global {
  interface Window {
    desktopApp?: {appearance:(value:string)=>Promise<void>;openSetup:()=>Promise<void>;chooseSpeech:()=>Promise<{name:string;restartRequired:boolean}|null|undefined>;openSpeechGuide:()=>Promise<void>};
  }
}
