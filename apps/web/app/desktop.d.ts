export {};

declare global {
  interface Window {
    desktopApp?: {openSetup:()=>Promise<void>};
  }
}
