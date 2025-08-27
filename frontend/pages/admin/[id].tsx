import { useRouter } from "next/router";
import useSWR from "swr";
import Layout from "../../layouts/Layout";
import { api, API, authHeaders } from "../../utils/api";
import { useEffect, useState } from "react";
const fetcher = (url:string)=>api.get(url).then(r=>r.data);
export default function EditPost(){
  const router = useRouter();
  const { id } = router.query;
  const { data:post } = useSWR(id?`/api/post_by_id/${id}`:null, fetcher);
  const [title, setTitle] = useState(""); const [content, setContent] = useState(""); const [imagePath, setImagePath] = useState<string|undefined>(undefined);
  const [file, setFile] = useState<File|undefined>(undefined);
  useEffect(()=>{ if(post){ setTitle(post.title); setContent(post.content); setImagePath(post.image_path); }},[post]);
  const upload = async ()=>{ if(!file) return; const fd = new FormData(); fd.append("file", file); const res = await fetch(`${API}/api/upload`, { method:"POST", headers: authHeaders() as any, body: fd }); const data = await res.json(); setImagePath(data.path); };
  const submit = async (e:any)=>{ e.preventDefault(); await api.put(`/api/posts/${id}`, { title, content, image_path: imagePath }, { headers: authHeaders() }); router.push("/"); };
  if(!post) return <Layout>Loading…</Layout>;
  return (<Layout>
    <h1>Edit Post</h1>
    <form onSubmit={submit} style={{display:"grid", gap:12, maxWidth:600}}>
      <input placeholder="Title" value={title} onChange={e=>setTitle(e.target.value)} required/>
      <textarea placeholder="Content" value={content} onChange={e=>setContent(e.target.value)} rows={8} required/>
      <input type="file" accept="image/*" onChange={e=>setFile(e.target.files?.[0] as File)}/>
      <button type="button" onClick={upload}>Upload Image</button>
      {imagePath && <img src={`${API}${imagePath}`} style={{maxWidth:240,borderRadius:8}}/>}
      <button type="submit">Save</button>
    </form>
  </Layout>);
}
