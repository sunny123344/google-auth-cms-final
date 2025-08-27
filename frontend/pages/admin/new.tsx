import { useState } from "react";
import Layout from "../../layouts/Layout";
import { API, api, authHeaders } from "../../utils/api";
export default function NewPost(){
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [imagePath, setImagePath] = useState<string|undefined>(undefined);
  const [file, setFile] = useState<File|undefined>(undefined);
  const upload = async ()=>{ if(!file) return; const fd = new FormData(); fd.append("file", file); const res = await fetch(`${API}/api/upload`, { method:"POST", headers: authHeaders() as any, body: fd }); const data = await res.json(); setImagePath(data.path); };
  const submit = async (e:any)=>{ e.preventDefault(); await api.post("/api/posts", { title, content, image_path: imagePath }, { headers: authHeaders() }); window.location.href="/"; };
  return (<Layout>
    <h1>New Post</h1>
    <form onSubmit={submit} style={{display:"grid", gap:12, maxWidth:600}}>
      <input placeholder="Title" value={title} onChange={e=>setTitle(e.target.value)} required/>
      <textarea placeholder="Content" value={content} onChange={e=>setContent(e.target.value)} rows={8} required/>
      <input type="file" accept="image/*" onChange={e=>setFile(e.target.files?.[0] as File)}/>
      <button type="button" onClick={upload}>Upload Image</button>
      {imagePath && <img src={`${API}${imagePath}`} style={{maxWidth:240,borderRadius:8}}/>}
      <button type="submit">Create</button>
    </form>
  </Layout>);
}
