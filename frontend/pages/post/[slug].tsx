import { useRouter } from "next/router";
import useSWR from "swr";
import { api, API } from "../../utils/api";
import Layout from "../../layouts/Layout";
const fetcher = (url:string)=>api.get(url).then(r=>r.data);
export default function PostPage(){
  const router = useRouter();
  const {slug} = router.query;
  const {data:post} = useSWR(slug?`/api/posts/${slug}`:null, fetcher);
  if(!post) return <Layout>Loading...</Layout>;
  return (<Layout>
    <h1>{post.title}</h1>
    {post.image_path && <img src={`${API}${post.image_path}`} style={{maxWidth:"100%",borderRadius:8}}/>}
    <p style={{whiteSpace:"pre-wrap"}}>{post.content}</p>
  </Layout>);
}
