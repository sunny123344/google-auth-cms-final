import useSWR from "swr";
import { api, API, authHeaders } from "../utils/api";
import Link from "next/link";
import Layout from "../layouts/Layout";
const fetcher = (url:string)=>api.get(url).then(r=>r.data);
export default function Home(){
  const {data:posts, mutate} = useSWR("/api/posts", fetcher);
  const del = async (id:number)=>{ if(!confirm("Delete this post?")) return; await api.delete(`/api/posts/${id}`, { headers: authHeaders() }); mutate(); };
  return (<Layout>
    <h1>All Posts</h1>
    <div style={{display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(260px,1fr))", gap:16}}>
      {posts?.map((p:any)=>(<div key={p.id} style={{border:"1px solid #ddd", borderRadius:10, padding:12}}>
        {p.image_path && <img src={`${API}${p.image_path}`} style={{width:"100%",height:160,objectFit:"cover",borderRadius:8}}/>}
        <h3>{p.title}</h3>
        <p style={{opacity:.7}}>{p.category?.name}</p>
        <div style={{display:"flex", gap:12, justifyContent:"space-between"}}>
          <Link href={`/post/${p.slug}`}>Read →</Link>
          <Link href={`/admin/${p.id}`}>Edit</Link>
          <button onClick={()=>del(p.id)} style={{color:"crimson"}}>Delete</button>
        </div>
      </div>))}
    </div>
  </Layout>);
}
