import {notFound} from 'next/navigation';
import CaptureCheck from './check';
export default function Page(){
  if(process.env.NODE_ENV!=='development')notFound();
  return <CaptureCheck/>;
}
