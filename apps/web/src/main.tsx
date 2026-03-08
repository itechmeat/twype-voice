import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./i18n";
import "./styles.css";

async function enableServiceWorker() {
  if (!import.meta.env.PROD) {
    return;
  }

  const { registerSW } = await import("virtual:pwa-register");
  registerSW({ immediate: true });
}

const rootElement = document.getElementById("root");

if (rootElement === null) {
  throw new Error("Root element '#root' was not found");
}

void enableServiceWorker();

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
