import Nav from "../components/Nav";
import React from "react";
export default function Layout({children}:{children:React.ReactNode}){ return (<div style={{maxWidth:960, margin:"0 auto", padding:20}}><Nav/><main style={{marginTop:20}}>{children}</main></div>); }
