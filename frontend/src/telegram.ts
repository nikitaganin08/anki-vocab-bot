interface TelegramThemeParams {
  bg_color?: string;
  text_color?: string;
  hint_color?: string;
  button_color?: string;
  button_text_color?: string;
  secondary_bg_color?: string;
}

interface TelegramBackButton {
  show: () => void;
  hide: () => void;
  onClick: (callback: () => void) => void;
  offClick: (callback: () => void) => void;
}

interface TelegramWebApp {
  initData: string;
  themeParams?: TelegramThemeParams;
  BackButton?: TelegramBackButton;
  ready?: () => void;
  expand?: () => void;
}

interface TelegramWindow extends Window {
  Telegram?: {
    WebApp?: TelegramWebApp;
  };
}

const THEME_VARIABLES: [keyof TelegramThemeParams, string][] = [
  ["bg_color", "--tg-bg"],
  ["text_color", "--tg-text"],
  ["hint_color", "--tg-hint"],
  ["button_color", "--tg-accent"],
  ["button_text_color", "--tg-accent-text"],
  ["secondary_bg_color", "--tg-surface"],
];

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

// Missing params stay unset so the light fallbacks in styles.css apply.
export function applyTelegramTheme(): void {
  const theme = getTelegramWebApp()?.themeParams ?? {};
  for (const [param, variable] of THEME_VARIABLES) {
    const value = theme[param];
    if (value) {
      document.documentElement.style.setProperty(variable, value);
    }
  }
}

export function showBackButton(onClick: () => void): () => void {
  const backButton = getTelegramWebApp()?.BackButton;
  if (!backButton) {
    return () => {};
  }

  backButton.onClick(onClick);
  backButton.show();
  return () => {
    backButton.offClick(onClick);
    backButton.hide();
  };
}
