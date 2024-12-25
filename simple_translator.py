import customtkinter

customtkinter.set_appearance_mode("dark")
app = customtkinter.CTk()
app.title("Simple Translator")

window_width = 600
window_height = 300

screen_width = app.winfo_screenwidth()
screen_height = app.winfo_screenheight()

x_coordinate = int((screen_width / 2) - (window_width / 2))
y_coordinate = int((screen_height / 2) - window_height)

app.geometry(f"{window_width}x{window_height}+{x_coordinate}+{y_coordinate}")
label = customtkinter.CTkLabel(
    app,
    text="Simple Translator",
    font=("Monotype Corsiva", 40, "bold"),
    text_color="#FF5733"
)
label.pack(pady=20)

frame = customtkinter.CTkFrame(app)
frame.pack(pady=10, fill="x", padx=40)

label_left = customtkinter.CTkLabel(frame, text="English", font=("Arial", 14))
label_left.pack(side="left", padx=80)

label_right = customtkinter.CTkLabel(frame, text="German", font=("Arial", 14))
label_right.pack(side="right", padx=80)

app.mainloop()
