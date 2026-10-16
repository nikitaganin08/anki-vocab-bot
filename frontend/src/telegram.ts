interface TelegramWebApp {
  initData: string;
  ready?: () => void;
  expand?: () => void;
}

interface TelegramWindow extends Window {
  Telegram?: {
    WebApp?: TelegramWebApp;
  };
}

function getTelegramWebApp(): TelegramWebApp | null {
  const webApp = (window as TelegramWindow).Telegram?.WebApp;
  if (!webApp || webApp.initData.length === 0) {
    return null;
  }

  return webApp;
}

export function hasTelegramWebAppContext(): boolean {
  return getTelegramWebApp() !== null;
}

export function getTelegramInitData(): string | null {
  return getTelegramWebApp()?.initData ?? null;
}

export function prepareTelegramWebApp(): void {
  const webApp = getTelegramWebApp();
  if (webApp === null) {
    return;
  }

  webApp.ready?.();
  webApp.expand?.();
}
