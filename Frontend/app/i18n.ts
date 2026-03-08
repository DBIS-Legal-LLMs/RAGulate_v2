import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

import de from "./locales/de/translation.json";
import en from "./locales/en/translation.json";

i18n
  .use(LanguageDetector) // ← erkennt Browsersprache automatisch
  .use(initReactI18next)
  .init({
    resources: {
      de: { translation: de },
      en: { translation: en },
    },
    fallbackLng: "de",
    interpolation: { escapeValue: false },
  });

export default i18n;
