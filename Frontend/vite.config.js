import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
    plugins: [react()],
    appType: 'spa',
    test: {
        environment: 'jsdom',
        globals: true,
        setupFiles: ['./src/test/setup.js'],
        include: ['src/**/*.test.{js,jsx}'],
    },
    build: {
        chunkSizeWarningLimit: 600,
        rollupOptions: {
            output: {
                manualChunks(id) {
                    if (id.includes('node_modules/recharts')) return 'recharts';
                    if (id.includes('node_modules/react-dom') || id.includes('node_modules/react/')) return 'react-vendor';
                    if (id.includes('node_modules/react-router')) return 'router';
                    if (id.includes('node_modules/axios')) return 'axios';
                },
            },
        },
    },
})
