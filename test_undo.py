import customtkinter as ctk

def enable_undo(entry, string_var=None):
    if not string_var:
        string_var = ctk.StringVar()
        entry.configure(textvariable=string_var)
        
    stack = [""]
    ptr = [0] # current position in stack
    
    def on_change(*args):
        val = string_var.get()
        if getattr(entry, '_is_undoing', False):
            return
        if not stack or stack[ptr[0]] != val:
            del stack[ptr[0]+1:]
            stack.append(val)
            ptr[0] += 1
            if len(stack) > 50:
                stack.pop(0)
                ptr[0] -= 1

    def on_undo(event):
        if ptr[0] > 0:
            entry._is_undoing = True
            ptr[0] -= 1
            val = stack[ptr[0]]
            string_var.set(val)
            entry._is_undoing = False
        return "break"

    string_var.trace_add("write", on_change)
    entry.bind("<Control-z>", on_undo, add="+")
    entry.bind("<Control-Z>", on_undo, add="+")

app = ctk.CTk()
e = ctk.CTkEntry(app)
e.pack()
enable_undo(e)

var = e.cget("textvariable")
print(var.trace_info())

# simulate typings
var.set("h")
var.set("he")
var.set("hey")

print("stack points =", getattr(e, '_is_undoing', False), "stack is", stack if 'stack' in locals() else 'hidden in closure')
print("value before undo:", var.get())
e.event_generate("<Control-z>")
print("value after undo:", var.get())
