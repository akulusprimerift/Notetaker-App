export {};

declare global {
  interface Window {
    desktopApp?: {platform:string;openMicrophoneSettings:()=>Promise<void>;onPower:(listener:(kind:string)=>void)=>()=>void;appearance:(value:string)=>Promise<void>;openSetup:()=>Promise<void>;chooseSpeech:()=>Promise<{name:string;restartRequired:boolean}|null|undefined>;openSpeechGuide:()=>Promise<void>};
  }
}
