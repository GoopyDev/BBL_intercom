from ui.main_window import ITMessenger


if __name__ == "__main__":
    app = ITMessenger()
    app.mainloop()

# Para compilar:
# pyinstaller --onefile --windowed --name BBL_Chat --icon=res/BBL_Chat.ico --add-data "res;res" --hidden-import=PIL --hidden-import=customtkinter --hidden-import=winshell --hidden-import=win32com --hidden-import=win32com.client main.py
