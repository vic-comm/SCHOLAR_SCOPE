import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { crx } from '@crxjs/vite-plugin'
import manifest from './manifest.json'

// https://vitejs.dev/config/
export default defineConfig({
  base: './',
  plugins: [
    react(),
    crx({ manifest }),
  ],
  server: {
    port: 5174, // Different port from your frontend
  },
})

// import { defineConfig } from "vite"
// import { viteStaticCopy } from "vite-plugin-static-copy"

// export default defineConfig({
//   plugins: [
//     viteStaticCopy({
//       targets: [
//         { src: "manifest.json", dest: "." },
//         { src: "popup.html", dest: "." }
//       ]
//     })
//   ],

//   build: {
//     outDir: "dist",
//     emptyOutDir: true,

//     rollupOptions: {
//       input: {
//         popup: "popup.html",
//         content: "src/content.js",
//         background: "src/background.js"
//       },

//       output: {
//         entryFileNames: "[name].js",
//         chunkFileNames: "chunks/[name].js",
//         assetFileNames: "assets/[name][extname]"
//       }
//     }
//   }
// })