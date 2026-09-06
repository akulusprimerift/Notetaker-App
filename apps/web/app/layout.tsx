import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = {title:'Notetaker — Your lecture library',description:'A private workspace for detailed lecture notes.'};
export default function Layout({children}:{children:React.ReactNode}) {
  return <html lang="en"><body>{children}</body></html>;
}
