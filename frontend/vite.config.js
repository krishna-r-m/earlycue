import {defineConfig} from "vite"
import react from "@vitejs/plugin-react"

export default defineConfig({
  plugins:[react()],
  server:{
    port:5173,
    host:true,
    watch:{usePolling:!!process.env.VITE_POLL},
    proxy:{"/api":{target:process.env.API_PROXY||"http://localhost:8000",changeOrigin:true}}
  }
})
