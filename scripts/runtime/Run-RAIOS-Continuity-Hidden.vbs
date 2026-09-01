Option Explicit

Dim shell, fso, scriptPath, repoPath, command, exitCode
If WScript.Arguments.Count <> 1 Then WScript.Quit 2

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptPath = fso.BuildPath(fso.GetParentFolderName(WScript.ScriptFullName), "Maintain-RAIOS-Online.ps1")
repoPath = WScript.Arguments(0)
command = "powershell.exe -NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File """ & scriptPath & """ -Repo """ & repoPath & """"
exitCode = shell.Run(command, 0, True)
WScript.Quit exitCode
