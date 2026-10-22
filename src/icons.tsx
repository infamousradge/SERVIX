const iconPaths:Record<string,string[]>={
  dashboard:['M4 4h6v6H4z','M14 4h6v4h-6z','M14 12h6v8h-6z','M4 14h6v6H4z'],
  intake:['M4 6h16v13H4z','M4 9l8 5 8-5','M8 3h8v3'],
  service:['M8 4h8','M9 2h6v4H9z','M6 5h12a2 2 0 0 1 2 2v14H4V7a2 2 0 0 1 2-2z','M8 11h8','M8 15h6'],
  clients:['M15.5 20v-1.4a4.1 4.1 0 0 0-4.1-4.1H6.6a4.1 4.1 0 0 0-4.1 4.1V20','M9 10.5a3.75 3.75 0 1 0 0-7.5 3.75 3.75 0 0 0 0 7.5z','M17.5 11.5a3 3 0 1 0 0-6','M21.5 20v-1.3a3.6 3.6 0 0 0-2.7-3.48'],
  equipment:['M5 4h14v12H5z','M8 8h8','M9 20h6','M12 16v4'],
  engineer:['M14.8 19.5v-1.2a4 4 0 0 0-4-4H7.2a4 4 0 0 0-4 4v1.2','M9 10.2a3.6 3.6 0 1 0 0-7.2 3.6 3.6 0 0 0 0 7.2z','M16 8l1.4 1.4L21 5.8','M18.7 3.9l1.4 1.4'],
  shield:['M12 3l7 3v5c0 4.8-2.8 8.1-7 10-4.2-1.9-7-5.2-7-10V6z','M9 12l2 2 4-4'],
  calibration:['M12 3v3','M12 18v3','M3 12h3','M18 12h3','M5.6 5.6l2.1 2.1','M16.3 16.3l2.1 2.1','M5.6 18.4l2.1-2.1','M16.3 7.7l2.1-2.1','M12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7z'],
  parts:['M5 7h14','M7 4v6','M17 4v6','M5 10h14v10H5z','M8 14h3','M13 14h3','M8 17h8'],
  documents:['M6 3h8l4 4v14H6z','M14 3v5h5','M9 12h6','M9 16h6'],
  reports:['M4 19V9','M10 19V5','M16 19v-7','M22 19V8','M3 21h20'],
  data:['M12 4c4.97 0 9 1.12 9 2.5S16.97 9 12 9 3 7.88 3 6.5 7.03 4 12 4z','M3 6.5v5C3 12.88 7.03 14 12 14s9-1.12 9-2.5v-5','M3 11.5v5C3 17.88 7.03 19 12 19s9-1.12 9-2.5v-5'],
  settings:['M4 7h10','M18 7h2','M14 5v4','M4 17h2','M10 17h10','M6 15v4','M4 12h5','M13 12h7','M9 10v4'],
  search:['M21 21l-4.35-4.35','M19 11a8 8 0 1 1-16 0 8 8 0 0 1 16 0z'],
  bell:['M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9','M10 21h4'],
  plus:['M12 5v14','M5 12h14'],
  refresh:['M20 6v5h-5','M4 18v-5h5','M18.5 9A7 7 0 0 0 6.2 6.2L4 8','M5.5 15a7 7 0 0 0 12.3 2.8L20 16'],
  chevron:['M9 18l6-6-6-6'],
  close:['M18 6L6 18','M6 6l12 12'],
  print:['M6 9V2h12v7','M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2','M6 14h12v8H6z'],
  export:['M12 3v12','M7 8l5-5 5 5','M5 21h14a2 2 0 0 0 2-2v-4','M3 15v4a2 2 0 0 0 2 2'],
  status:['M4 12a8 8 0 1 0 8-8','M4 4v6h6','M9 12l2 2 4-5'],
  payment:['M3 6h18v12H3z','M3 10h18','M16 14h2'],
  quote:['M6 3h9l3 3v15H6z','M14 3v4h4','M9 11h6','M9 15h6'],
  flag:['M5 21V4','M5 5h11l-2 4 2 4H5'],
  calendar:['M4 5h16v16H4z','M8 3v4','M16 3v4','M4 10h16'],
  tag:['M20 13l-7 7-9-9V4h7z','M8.5 8.5h.01'],
  user:['M20 21a8 8 0 0 0-16 0','M12 13a5 5 0 1 0 0-10 5 5 0 0 0 0 10z'],
  info:['M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z','M12 10v6','M12 7h.01']
};
function Icon({name,size=18,className=''}:{name:string,size?:number,className?:string}){
  return <svg className={`icon ${className}`} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{(iconPaths[name]||iconPaths.service).map((d,i)=><path key={i} d={d}/>)}</svg>;
}
