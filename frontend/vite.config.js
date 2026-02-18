import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { fileURLToPath, URL } from 'node:url';
export default defineConfig({
    plugins: [vue()],
    resolve: {
        alias: {
            '@': fileURLToPath(new URL('./src', import.meta.url))
        }
    },
    server: {
        port: 5173,
        proxy: {
            '/api': {
                target: 'http://localhost:8000',
                changeOrigin: true,
                rewrite: function (path) { return path.replace(/^\/api/, ''); },
                configure: function (proxy, options) {
                    proxy.on('proxyRes', function (proxyRes, req, res) {
                        // Ensure streaming responses aren't buffered
                        proxyRes.headers['x-accel-buffering'] = 'no';
                    });
                }
            }
        }
    }
});
