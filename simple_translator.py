import customtkinter

class SimpleTranslatorApp:
    def __init__(self, root):
        self.root = root

        # Set appearance mode and title
        customtkinter.set_appearance_mode("dark")
        self.root.title("Simple Translator")

        # Set window geometry
        window_width = 600
        window_height = 300
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x_coordinate = int((screen_width / 2) - (window_width / 2))
        y_coordinate = int((screen_height / 2) - window_height)
        self.root.geometry(f"{window_width}x{window_height}+{x_coordinate}+{y_coordinate}")

        # Distribute the columns evenly across the grid
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_columnconfigure(2, weight=1)

        # Create UI elements
        self.create_widgets()

    def create_widgets(self):
        # Header for the application
        self.label_header = customtkinter.CTkLabel(
            self.root,
            text="Simple Translator ",
            font=("Monotype Corsiva", 40, "bold"),
            text_color="#FF5733"
        )
        self.label_header.grid(row=0, column=0, columnspan=3, pady=20)

        # Labels for the languages
        self.label_left = customtkinter.CTkLabel(self.root, text="English", font=("Arial", 14))
        self.label_left.grid(row=1, column=0, padx=20, pady=(5, 0), sticky="n")

        self.label_right = customtkinter.CTkLabel(self.root, text="German", font=("Arial", 14))
        self.label_right.grid(row=1, column=2, padx=20, pady=(5, 0), sticky="n")

        # Input fields
        self.entry_left = customtkinter.CTkEntry(self.root, width=200, justify="center")
        self.entry_left.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        self.entry_right = customtkinter.CTkEntry(self.root, width=200, justify="center")
        self.entry_right.grid(row=2, column=2, padx=20, pady=10, sticky="ew")

        # Buttons
        self.switch_button = customtkinter.CTkButton(self.root, text="Switch", command=self.switch_languages, width=80)
        self.switch_button.grid(row=2, column=1, padx=20, pady=10)

        self.translate_button = customtkinter.CTkButton(self.root, text="Translate", command=self.translate_text, width=160, height=40)
        self.translate_button.grid(row=3, column=1, padx=20, pady=10)

    def switch_languages(self):
        # Function to switch the languages
        left_text = self.label_left.cget("text")
        right_text = self.label_right.cget("text")
        self.label_left.configure(text=right_text)
        self.label_right.configure(text=left_text)

    def translate_text(self):
        # Placeholder for translation logic
        left_input = self.entry_left.get()
        # Add translation logic here
        self.entry_right.delete(0, "end")
        self.entry_right.insert(0, left_input)  # For demonstration, copy text


if __name__ == "__main__":
    root = customtkinter.CTk()
    app = SimpleTranslatorApp(root)
    root.mainloop()
