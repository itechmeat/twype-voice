import { useEffect, useState } from "react";
import { useRegisterSW } from "virtual:pwa-register/react";
import { App, type ServiceWorkerPromptState } from "./App";
import { appRouter } from "./router";

const noop = () => undefined;
const inactiveServiceWorkerPrompt: ServiceWorkerPromptState = {
  needRefresh: false,
  onUpdate: noop,
  resetSignal: 0,
};

function ProductionApp() {
  const [resetSignal, setResetSignal] = useState(0);
  const {
    needRefresh: [needRefresh],
    updateServiceWorker,
  } = useRegisterSW({
    onNeedRefresh() {
      setResetSignal((value) => value + 1);
    },
    onOfflineReady: noop,
  });

  useEffect(() => {
    return appRouter.subscribe(() => {
      setResetSignal((value) => value + 1);
    });
  }, []);

  return (
    <App
      serviceWorkerPrompt={{
        needRefresh,
        onUpdate() {
          void updateServiceWorker(true);
        },
        resetSignal,
      }}
    />
  );
}

export function RootApp() {
  if (!import.meta.env.PROD) {
    return <App serviceWorkerPrompt={inactiveServiceWorkerPrompt} />;
  }

  return <ProductionApp />;
}
