import Link from "next/link";
import { useEffect, useState } from "react";
import { API } from "../utils/api";
export default function Nav(){
  const [user, setUser] = useState<any>(null);
  useEffect(()=>{ const token = localStorage.getItem("token"); if(!token) return; fetch(`${API}/api/me`, { headers:{ Authorization:`Bearer ${token}`}}).then(r=>r.json()).then(d=>{ if(d?.authenticated) setUser(d.user); else setUser(null); }); },[]);
  return (<nav style={{display:"flex", alignItems:"center", gap:16, justifyContent:"space-between"}}>
    <div style={{display:"flex", gap:12, alignItems:"center"}}>
      <Link href="/">Home</Link>
      <Link href="/admin/new">New Post</Link>
    </div>
    <div>
      {!user ? (<a href={`${API}/auth/google`} style={{padding:"8px 12px", border:"1px solid #ccc", borderRadius:8}}>Login with Google</a>) :
      (<div style={{display:"flex", gap:12, alignItems:"center"}}>{user.picture && <img src={user.picture} style={{width:28, height:28, borderRadius:14}}/>}<span>{user.name||user.email}</span></div>)}
    </div>
  </nav>);
}
