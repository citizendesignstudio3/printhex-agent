import tkinter as tk

def manual_status_popup(send_event):

    window = tk.Tk()
    window.title("Manual Machine Status")

    tk.Label(window, text="Machine Status").pack(pady=10)

    def send_running():
        send_event("MANUAL_STATUS", {"running": True})
        window.destroy()

    def send_stopped():
        send_event("MANUAL_STATUS", {"running": False})
        window.destroy()

    tk.Button(window, text="Machine Running", command=send_running).pack(pady=5)
    tk.Button(window, text="Machine Stopped", command=send_stopped).pack(pady=5)

    window.mainloop()
