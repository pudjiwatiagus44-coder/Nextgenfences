Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
ScriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = ScriptDir

' Collect arguments
Args = ""
For Each Arg In WScript.Arguments
    Args = Args & " " & Arg
Next

' Run pythonw with arguments
WshShell.Run "pythonw main.py" & Args, 0, False