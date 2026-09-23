export {};

declare global {
  interface Window {
    desktopApp?: {openSetup:()=>Promise<void>;chooseSpeech:()=>Promise<{name:string;restartRequired:boolean}|null|undefined>;openSpeechGuide:()=>Promise<void>};
  }
}
