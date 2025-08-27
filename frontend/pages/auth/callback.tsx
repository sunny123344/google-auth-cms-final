import { useRouter } from "next/router";
import { useEffect } from "react";
export default function Callback(){
  const router = useRouter();
  useEffect(()=>{ const url = new URL(window.location.href); const token = url.searchParams.get("token"); if(token){ localStorage.setItem("token", token); router.replace("/"); } else { router.replace("/"); } },[]);
  return <p style={{padding:20}}>Signing you in…</p>;
}
