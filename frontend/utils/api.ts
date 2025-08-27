import axios from "axios";
export const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:4000";
export const api = axios.create({ baseURL: API, withCredentials: false });
export function authHeaders(){ if(typeof window === "undefined") return {}; const t=localStorage.getItem("token"); return t?{Authorization:`Bearer ${t}`}:{ }; }
