' Double-click to open the GUI with no console window.
Option Explicit
Dim sh, fso, appDir, pyw, py, script, cmd, args, i
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
appDir = fso.GetParentFolderName(WScript.ScriptFullName)
script = appDir & "\subtitle_translator_app.py"

pyw = sh.ExpandEnvironmentStrings("%LocalAppData%") & "\Programs\Python\Python312\pythonw.exe"
If Not fso.FileExists(pyw) Then pyw = ""
If pyw = "" Then
  On Error Resume Next
  pyw = sh.RegRead("HKCU\Software\Python\PythonCore\3.12\InstallPath\") & "pythonw.exe"
  If Err.Number <> 0 Then Err.Clear : pyw = ""
  On Error GoTo 0
End If

args = ""
For i = 0 To WScript.Arguments.Count - 1
  args = args & " """ & WScript.Arguments(i) & """"
Next

If pyw <> "" And fso.FileExists(pyw) Then
  cmd = """" & pyw & """ """ & script & """" & args
Else
  cmd = "pythonw """ & script & """" & args
End If

sh.CurrentDirectory = appDir
sh.Run cmd, 0, False
