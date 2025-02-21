import customtkinter as ctk
import requests
import re
import json
from googletrans import Translator
from spellchecker import SpellChecker
import textdistance
from abc import ABC, abstractmethod


# === Utility-Klasse ===
class Utils:
    @staticmethod
    def load_config(api_name=None):
        """Lädt die Konfigurationsdatei und gibt API-spezifische Einstellungen zurück."""
        try:
            with open(CONFIG_FILE_PATH, "r") as config_file:
                config = json.load(config_file)
            if api_name:
                api_config = config.get(api_name)
                if not api_config:
                    raise KeyError(f"Fehlende Konfiguration für {api_name} in {CONFIG_FILE_PATH}")
                return api_config
            return config
        except FileNotFoundError:
            raise Exception(f"Konfigurationsdatei {CONFIG_FILE_PATH} nicht gefunden!")
        except json.JSONDecodeError:
            raise Exception(f"Fehler beim Einlesen der JSON-Datei {CONFIG_FILE_PATH}!")
        except KeyError as e:
            raise Exception(str(e))

    @staticmethod
    def validate_input(value):
        pattern = "^[a-zA-ZäöüÄÖÜß]*$"
        return bool(re.match(pattern, value))


# === Model ===
class TranslatorStrategy(ABC):
    @abstractmethod
    def translate(self, text, source_lang, target_lang):
        pass


class DeepLTranslator(TranslatorStrategy):
    def __init__(self):
        try:
            config = Utils.load_config("DeepL")

            # Direkter Zugriff mit eckigen Klammern -> KeyError, falls der Schlüssel fehlt
            self.api_key = config["api_key"]
            self.api_url = config["api_url"]

            # Falls einer der Werte leer ist, wird eine ValueError ausgelöst
            if not self.api_key or not self.api_url:
                raise ValueError("DeepL-Konfiguration enthält leere Werte für 'api_key' oder 'api_url'.")

        except KeyError as e:
            raise Exception(f"Fehlende Konfiguration für DeepL: {e}")
        except ValueError as e:
            raise Exception(f"Ungültige Konfiguration für DeepL: {e}")

    def translate(self, text, source_lang, target_lang):
        params = {"auth_key": self.api_key,
                  "text": text,
                  "source_lang": source_lang.upper(),
                  "target_lang": target_lang.upper(),
                  }

        try:
            response = requests.post(self.api_url, data=params)
            response.raise_for_status()
            result = response.json()
            if "translations" in result and len(result["translations"]) > 0:
                return result["translations"][0]["text"], "DeepL"
            return None, "DeepL"

        except requests.exceptions.RequestException as e:
            print(f"[DeepL API-Fehler] {e}")
            return None, "DeepL"

        except AttributeError as e:
            print(f"[DeepL Fehler] {e}")
            return None, "DeepL"

        except Exception as e:  # Falls unerwartete Fehler auftreten
            print(f"[DeepL Unbekannter Fehler] {e}")
            return None, "DeepL"


class GoogleTranslator(TranslatorStrategy):
    def __init__(self):
        self.translator = Translator()

    def translate(self, text, source_lang, target_lang):
        try:
            # Google Translate erwartet lower-case Sprachcodes (z. B. "en" statt "EN")
            source_lang = source_lang.lower()
            target_lang = target_lang.lower()

            result = self.translator.translate(text, src=source_lang, dest=target_lang)

            # Falls das Ergebnis kein gültiges Objekt ist, AttributeError werfen
            if not hasattr(result, "text"):
                raise AttributeError("Objekt ist leer oder ungültig")

            return result.text, "Google Translate"

        except AttributeError as e:
            print(f"[Google Translate Fehler] {e}")
            return None, "Google Translate"

        except requests.exceptions.RequestException as e:
            print(f"[Google Translate API-Fehler] {e}")
            return None, "Google Translate"

        except Exception as e:
            print(f"[Google Translate Unbekannter Fehler] {e}")
            return None, "Google Translate"


class FallbackTranslator(TranslatorStrategy):
    def __init__(self, translators):
        if not translators:
            raise ValueError("Die Liste der Übersetzer darf nicht leer sein.")
        self.translators = translators

    def translate(self, text, source_lang, target_lang):
        for translator in self.translators:
            name = type(translator).__name__  # Setzt `name` als den Klassennamen des Translators
            try:
                result, name = translator.translate(text, source_lang, target_lang)
                if result is not None:
                    return result, name
            except Exception as e:
                print(f"[Fehler bei {name}] {e}")
                continue  # Falls ein Fehler auftritt, probiere den nächsten

        return "Translation failed.", "No API worked"


class TranslatorModel:
    def __init__(self):
        # Liste der verfügbaren APIs
        available_translators = [DeepLTranslator(), GoogleTranslator()]
        self.translator = FallbackTranslator(available_translators)

    def translate_text(self, text, source_lang, target_lang):
        return self.translator.translate(text, source_lang, target_lang)

    def is_in_dict(self, text, language):
        return text in SpellChecker(language=language)
    """
    def fuzzy_search(self, word, language, n=8):
        spell = SpellChecker(language=language)
        word_list = list(spell.word_frequency.dictionary.keys())
        if not word_list:
            return [word]
        return sorted(word_list, key=lambda w: textdistance.damerau_levenshtein(word.lower(), w.lower()))[:n]
    """

    def fuzzy_search(self, word, language, n=8, max_distance=1):
        spell = SpellChecker(language=language)
        word_list = list(spell.word_frequency.dictionary.keys())

        if not word_list:  # Falls keine Wörter vorhanden sind
            return [word]

        # Berechne den Ähnlichkeitswert für jedes Wort
        similar_words = sorted(
            word_list,
            key=lambda w: textdistance.damerau_levenshtein(word.lower(), w.lower())
        )

        # Filtere Wörter, die einen Abstand von `max_distance` haben und mit dem gleichen Buchstaben starten
        filtered_words = [
            w for w in similar_words
            if textdistance.damerau_levenshtein(word.lower(), w.lower()) <= max_distance
               and w.lower().startswith(word.lower()[0])  # 👈 Gleicher erster Buchstabe
        ]

        # Gebe maximal `n` Wörter zurück, aber keine zufälligen Wörter
        return filtered_words[:min(n, len(filtered_words))]


# === View ===
class TranslatorView:
    def __init__(self, root, controller):
        self.root = root
        self.controller = controller
        self.suggestion_buttons = []
        self.setup_ui()

    def setup_ui(self):

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")

        # Custom Theme Settings
        custom_fonts = {
            "header": ("Poppins", 35, "bold"),
            "label": ("Roboto", 18, "bold"),
            "button": ("Montserrat", 16, "bold"),
            "entry": ("Inter", 16, "bold"),
            "status": ("Roboto", 18, "bold"),
            "suggestion": ("Montserrat", 14, "italic", "bold")
        }

        custom_colors = {
            "header": "#A3E135",
            "label": "#D1D5DB",
            "button_text": "white",
            "button_bg": "#4CAF50",
            "button_hover": "#388E3C",
            "entry_text": "#E5E7EB",
            "entry_bg": "#005c29",
            "entry_border": "#66BB6A",
            "entry_placeholder": "#9CA3AF",
            "status_bg": "#4CAF50",
            "suggestion_bg": "#1E1E1E",
            "suggestion_text": "#A3E635"
        }

        # Title - Appbar
        self.root.title("Simple Translator Vers. 1.0")
        # App Size
        window_width, window_height = 400, 700
        # Calculate Middle Of The Screen
        screen_width, screen_height = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        x_coordinate, y_coordinate = (screen_width - window_width) // 2, (screen_height - window_height) // 2
        # Put The App In The Middle Of The Screen
        self.root.geometry(f"{window_width}x{window_height}+{x_coordinate}+{y_coordinate}")

        # Configure The Grid
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(6, weight=0)  # Dynamischer Platz über den Vorschlägen
        self.root.grid_rowconfigure(7, weight=0)  # Vorschläge bleiben fix
        self.root.grid_rowconfigure(8, weight=1)  # Statusleiste bleibt fixiert
        self.root.grid_rowconfigure(9, weight=0)

        # Title
        self.label_header = ctk.CTkLabel(self.root,
                                         text="Simple Translator",
                                         font=custom_fonts["header"],
                                         text_color=custom_colors["header"],

                                         )
        self.label_header.grid(row=0, column=0, columnspan=3, pady=20)

        # Input Field Label
        self.label_left = ctk.CTkLabel(self.root,
                                       text="English",
                                       font=custom_fonts["label"],
                                       text_color=custom_colors["label"])
        self.label_left.grid(row=1, column=0, columnspan=3, padx=20, pady=(6, 0))

        # Output Field Label
        self.label_right = ctk.CTkLabel(self.root,
                                        text="German",
                                        font=custom_fonts["label"],
                                        text_color=custom_colors["label"])
        self.label_right.grid(row=4, column=0, columnspan=3, padx=20, pady=(6, 0))

        # Input Field Entry
        self.entry_left = ctk.CTkEntry(self.root,
                                       width=200,
                                       corner_radius=20,
                                       font=custom_fonts["entry"], text_color=custom_colors["entry_text"],
                                       fg_color=custom_colors["entry_bg"],
                                       border_color=custom_colors["entry_border"],
                                       placeholder_text_color=custom_colors["entry_placeholder"],
                                       justify="center",
                                       height=34,
                                       validate="key",
                                       validatecommand=(self.root.register(Utils.validate_input), "%P"))
        self.entry_left.grid(row=2, column=0, columnspan=3, padx=60, pady=0, sticky="ew")

        # Output Field Entry
        self.entry_right = ctk.CTkEntry(self.root,
                                        width=200,
                                        font=custom_fonts["entry"], text_color=custom_colors["entry_text"],
                                        fg_color=custom_colors["entry_bg"],
                                        border_color=custom_colors["entry_border"],
                                        placeholder_text_color=custom_colors["entry_placeholder"],
                                        justify="center",
                                        height=34,
                                        corner_radius=20)
        self.entry_right.grid(row=5, column=0, columnspan=3, padx=60, pady=0, sticky="ew")
        self.entry_right.bind("<Key>", lambda e: None if (e.keysym == "c" and (e.state & 0x4)) else "break")

        # Switch Button
        self.switch_button = ctk.CTkButton(self.root,
                                           text="Switch",
                                           corner_radius=20,
                                           font=custom_fonts["button"],
                                           text_color=custom_colors["button_text"],
                                           fg_color=custom_colors["button_bg"],
                                           hover_color=custom_colors["button_hover"],
                                           command=self.switch_languages,
                                           width=80,
                                           height=34)
        self.switch_button.grid(row=3, column=0, columnspan=3, padx=80, pady=15)

        # Translate Button
        self.translate_button = ctk.CTkButton(self.root,
                                              text="Translate",
                                              corner_radius=20,
                                              font=custom_fonts["button"],
                                              text_color=custom_colors["button_text"],
                                              fg_color=custom_colors["button_bg"],
                                              hover_color=custom_colors["button_hover"],
                                              command=self.controller.translate_text,
                                              height=34)
        self.translate_button.grid(row=6, column=0, columnspan=3, padx=20, pady=15)

        # Status Label
        self.status_label = ctk.CTkLabel(self.root,
                                         text="Ready",
                                         text_color=custom_colors["button_text"],
                                         font=custom_fonts["status"],
                                         fg_color=custom_colors["status_bg"],
                                         height=30)
        self.status_label.grid(row=9, column=0, columnspan=3, padx=0, pady=(5, 0), sticky="nsew")

        self.suggestion_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.suggestion_frame.grid(row=7, column=0, columnspan=3, pady=(0, 0))
        self.suggestion_label = ctk.CTkLabel(
            self.suggestion_frame,
            text="Did You Mean:",
            font=custom_fonts["suggestion"],
            text_color=custom_colors["suggestion_text"]
        )
        self.suggestion_label.pack(side="top", pady=(5, 2))
        self.suggestion_label.pack_forget()

        self.suggestion_button_config = {
            "corner_radius": 20,
            "width": 200,
            "fg_color": "#4CAF50",
            "hover_color": "#388E3C",
            "text_color": "white",
            "font": ("Poppins", 16, "bold")
        }

    def switch_languages(self):
        """Wechselt die Sprachen und leert das rechte Eingabefeld."""
        left_text = self.label_left.cget("text")
        right_text = self.label_right.cget("text")
        self.label_left.configure(text=right_text)
        self.label_right.configure(text=left_text)
        # Leere das rechte Eingabefeld
        self.entry_right.delete(0, "end")

    def get_input_text(self):
        return self.entry_left.get()

    def get_source_language(self):
        return "en" if self.label_left.cget("text") == "English" else "de"

    def get_target_language(self):
        return "de" if self.get_source_language() == "en" else "en"

    def set_input_text(self, text):
        self.entry_left.delete(0, "end")
        self.entry_left.insert(0, text)

    def show_translation(self, translation, api_used):
        self.clear_suggestions()
        self.entry_right.delete(0, "end")
        input_text = self.get_input_text()
        if self.get_source_language() == "de":

            if input_text.isupper():  # Falls die gesamte Eingabe groß ist
                translation = translation.upper()
            else:  # Sonst immer klein
                translation = translation.lower()

        if self.get_source_language() == "en":
            if input_text.isupper():
                translation = translation.upper()  # Wenn die Eingabe komplett groß ist, bleibt die Übersetzung groß
            else:
                translation = translation.capitalize()  # Erster Buchstabe groß, Rest klein

        self.entry_right.insert(0, translation)
        self.status_label.configure(text=f"Translated with {api_used}", text_color="black")

    def show_status(self, message, color="#7a0000"):
        self.status_label.configure(text=message, text_color=color)

    def show_suggestions(self, suggestions):
        # Zeigt die gefundenen Wortvorschläge in der GUI an.
        self.clear_suggestions()

        if suggestions:
            self.suggestion_frame.grid()
            self.suggestion_label.pack(side="top", pady=(5, 2))

            for suggestion in suggestions:
                # Button mit gespeicherten Standardwerten erstellen
                btn = ctk.CTkButton(
                    self.suggestion_frame,
                    text=suggestion,
                    command=lambda s=suggestion: self.controller.on_suggestion_click(s),
                    **self.suggestion_button_config
                )
                btn.pack(side="top", padx=10, pady=2)  # Button sichtbar machen
                self.suggestion_buttons.append(btn)  # Speichern

        else:
            self.suggestion_frame.grid_remove()  # Falls keine Vorschläge, Frame verstecken
            self.suggestion_label.pack_forget()  # Label ausblenden

    def _create_suggestion_btn(self, suggestion):
        btn = ctk.CTkButton(self.suggestion_frame,
                            text=suggestion,
                            command=lambda: self.controller.on_suggestion_click(suggestion))
        btn.pack(side="left", padx=5, pady=5)
        self.suggestion_buttons.append(btn)

    def clear_suggestions(self):
        # Entfernt alle aktuell angezeigten Vorschlags-Buttons.

        for btn in self.suggestion_buttons:
            btn.destroy()
        self.suggestion_buttons = []
        self.suggestion_label.pack_forget()


# === Controller ===
class TranslatorController:
    def __init__(self, model, view):
        self.model = model
        self.view = view

    def translate_text(self):
        text = self.view.get_input_text().strip()
        source_lang = self.view.get_source_language()
        target_lang = self.view.get_target_language()

        if not text:
            self.view.entry_right.delete(0, "end")
            self.view.show_status("No input given")
            return

        if not self.model.is_in_dict(text, source_lang):
            self.view.entry_right.delete(0, "end")
            # self.view.show_status("No translation available.", "red")
            self.view.show_status("Translation failed")
            suggestions = self.model.fuzzy_search(text, source_lang)
            return self.view.show_suggestions(suggestions)

        translation, api_used = self.model.translate_text(text, source_lang, target_lang)
        if translation:
            self.view.show_translation(translation, api_used)
        else:
            self.view.show_status("Translation failed")

    def switch_languages(self):
        self.view.switch_languages()

    def clear_suggestions(self):
        self.view.clear_suggestions()

    def on_suggestion_click(self, suggestion):
        self.view.set_input_text(suggestion)


# === Main ===
CONFIG_FILE_PATH = "config.json"
if __name__ == "__main__":
    root = ctk.CTk(fg_color="#121212")
    model = TranslatorModel()
    controller = TranslatorController(model, None)
    view = TranslatorView(root, controller)
    controller.view = view
    root.mainloop()
