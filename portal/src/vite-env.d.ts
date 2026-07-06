/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_EXCHANGE_URL: string
  readonly VITE_QUANT_URL: string
  readonly VITE_EXCHANGE_DASH: string
  readonly VITE_QUANT_DASH: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
