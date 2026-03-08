import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./en.json";
import ru from "./ru.json";

const STORAGE_KEY = "twype:language";

function detectLanguage(): string {
  if (typeof window === "undefined") return "en";

  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === "en" || stored === "ru") return stored;

  const browserLang = navigator.language.slice(0, 2);
  return browserLang === "ru" ? "ru" : "en";
}

void i18n.use(initReactI18next).init({
  fallbackLng: "en",
  interpolation: { escapeValue: false },
  lng: detectLanguage(),
  resources: { en: { translation: en }, ru: { translation: ru } },
});

export { STORAGE_KEY };
export default i18n;
