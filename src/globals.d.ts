declare const React: any;
declare const ReactDOM: any;
declare namespace JSX { interface IntrinsicElements { [elementName: string]: any } }
interface Window {
  __TAURI__?: { core?: { invoke?: (command: string, args?: Record<string, unknown>) => Promise<any> } };
}
