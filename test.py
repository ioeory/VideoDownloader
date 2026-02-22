import customtkinter as ctk

def apply_undo_to_entry(entry):
    entry._undo_stack = [""]
    entry._undo_flag = False

    def on_key_release(event):
        if getattr(event, 'keysym', None) and event.keysym.lower() == 'z' and (event.state & 4):
            return
        if entry._undo_flag:
            return
        current = entry.get()
        stack = entry._undo_stack
        if not stack or stack[-1] != current:
            stack.append(current)
            if len(stack) > 30:
                stack.pop(0)

    def on_undo(event):
        stack = entry._undo_stack
        if len(stack) > 1:
            entry._undo_flag = True
            stack.pop()
            val = stack[-1]
            entry.delete(0, "end")
            entry.insert(0, val)
            entry.after(10, lambda: setattr(entry, '_undo_flag', False))
        return "break"

    entry.bind("<KeyRelease>", on_key_release)
    entry.bind("<Control-z>", on_undo)
    entry.bind("<Control-Z>", on_undo)

app = ctk.CTk()
e = ctk.CTkEntry(app)
e.pack()
apply_undo_to_entry(e)

# simulate typing
e.insert("end", "h")
e.event_generate("<KeyRelease>", keysym="h", state=0)
e.insert("end", "e")
e.event_generate("<KeyRelease>", keysym="e", state=0)
e.insert("end", "y")
e.event_generate("<KeyRelease>", keysym="y", state=0)

print(e._undo_stack)
e.event_generate("<Control-z>", state=4)
print("After undo:", e.get())
